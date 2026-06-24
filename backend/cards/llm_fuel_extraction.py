from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .models import CardPolicy

JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

MAX_LLM_INPUT_CHARS = 12000
SUPPORTED_DISCOUNT_TYPES = {
    CardPolicy.DiscountType.PER_LITER,
    CardPolicy.DiscountType.PERCENTAGE,
    CardPolicy.DiscountType.FIXED_AMOUNT,
}


@dataclass(frozen=True, slots=True)
class LineNumberedDocument:
    raw_text: str
    numbered_text: str
    lines: tuple[str, ...]
    input_truncated: bool

    def section_text(self, start_line: int, end_line: int) -> str:
        selected = self.lines[start_line - 1 : end_line]
        return "\n".join(selected)


@dataclass(frozen=True, slots=True)
class FuelTierData:
    fuel_type: str
    min_performance_amount: int
    discount_type: str
    discount_value: Decimal
    brand_scope: str
    min_payment_amount: int | None
    monthly_discount_limit: int | None


@dataclass(frozen=True, slots=True)
class ValidatedFuelExtraction:
    tier_data: FuelTierData | None
    normalized_payload: JsonObject
    warnings: list[str]


class CardInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str = ""
    issuer: str = ""


class FuelSection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    section_title: str = ""
    start_line: int
    end_line: int
    evidence_text: str
    reason: str = ""


class FuelBenefit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    category: str
    fuel_type: str = "ALL"
    discount_type: str
    discount_value: Decimal
    brand_scope: str = "all"
    min_payment_amount: int | None = None
    max_discount_amount: int | None = None
    monthly_discount_limit: int | None = None
    evidence_section_index: int
    evidence_text: str


class ExtractionQuality(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    extraction_confidence: str = "0"
    verification_status: str = CardPolicy.VerificationStatus.UNVERIFIED
    warnings: list[str] = Field(default_factory=list)


class LlmFuelPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    card: CardInfo = Field(default_factory=CardInfo)
    fuel_sections: list[FuelSection] = Field(default_factory=list)
    benefits: list[FuelBenefit] = Field(default_factory=list)
    quality: ExtractionQuality = Field(default_factory=ExtractionQuality)


def build_line_numbered_document(raw_text: str, max_chars: int = MAX_LLM_INPUT_CHARS) -> LineNumberedDocument:
    source_text = str(raw_text or "")
    input_truncated = len(source_text) > max_chars
    clipped_text = source_text[:max_chars]
    lines = tuple(clipped_text.splitlines() or [""])
    numbered_lines = [f"[{index:03d}] {line}" for index, line in enumerate(lines, start=1)]
    return LineNumberedDocument(
        raw_text=clipped_text,
        numbered_text="\n".join(numbered_lines),
        lines=lines,
        input_truncated=input_truncated,
    )


def validate_llm_fuel_payload(document: LineNumberedDocument, llm_payload: JsonObject) -> ValidatedFuelExtraction:
    warnings: list[str] = []
    try:
        parsed = LlmFuelPayload.model_validate(llm_payload)
    except ValidationError:
        return ValidatedFuelExtraction(
            tier_data=None,
            normalized_payload={"quality": {"warnings": ["invalid_llm_payload_schema"]}},
            warnings=["invalid_llm_payload_schema"],
        )

    warnings.extend(parsed.quality.warnings)
    if document.input_truncated:
        warnings.append("input_truncated")

    valid_sections = _validate_sections(document, parsed.fuel_sections, warnings)
    tier_data = _first_valid_tier(parsed.benefits, valid_sections, warnings)
    normalized_payload = parsed.model_dump(mode="json")
    _copy_gemini_metadata(llm_payload, normalized_payload)
    quality = normalized_payload.setdefault("quality", {})
    if isinstance(quality, dict):
        quality["warnings"] = warnings
    return ValidatedFuelExtraction(
        tier_data=tier_data,
        normalized_payload=normalized_payload,
        warnings=warnings,
    )


def _copy_gemini_metadata(source_payload: JsonObject, normalized_payload: JsonObject) -> None:
    model = source_payload.get("model")
    if isinstance(model, str):
        normalized_payload["model"] = model
    usage_metadata = source_payload.get("usage_metadata")
    if isinstance(usage_metadata, dict):
        normalized_payload["usage_metadata"] = usage_metadata
    cost_estimate = source_payload.get("cost_estimate")
    if isinstance(cost_estimate, dict):
        normalized_payload["cost_estimate"] = cost_estimate


def _validate_sections(
    document: LineNumberedDocument,
    sections: list[FuelSection],
    warnings: list[str],
) -> dict[int, FuelSection]:
    valid_sections: dict[int, FuelSection] = {}
    for index, section in enumerate(sections):
        if section.start_line < 1 or section.end_line > len(document.lines) or section.start_line > section.end_line:
            warnings.append("fuel_section_line_range_invalid")
            continue
        section_text = document.section_text(section.start_line, section.end_line)
        if section.evidence_text.strip() not in section_text:
            warnings.append("fuel_section_evidence_not_in_source")
            continue
        valid_sections[index] = section
    return valid_sections


def _first_valid_tier(
    benefits: list[FuelBenefit],
    valid_sections: dict[int, FuelSection],
    warnings: list[str],
) -> FuelTierData | None:
    for benefit in benefits:
        tier_data = _tier_from_benefit(benefit, valid_sections, warnings)
        if tier_data is not None:
            return tier_data
    return None


def _tier_from_benefit(
    benefit: FuelBenefit,
    valid_sections: dict[int, FuelSection],
    warnings: list[str],
) -> FuelTierData | None:
    if benefit.category != "fuel":
        warnings.append("non_fuel_benefit_ignored")
        return None
    if benefit.evidence_section_index not in valid_sections:
        warnings.append("benefit_evidence_section_missing")
        return None
    if benefit.discount_type not in SUPPORTED_DISCOUNT_TYPES:
        warnings.append("unsupported_discount_type")
        return None
    if benefit.discount_value <= 0:
        warnings.append("non_positive_discount_value")
        return None
    section = valid_sections[benefit.evidence_section_index]
    section_text = section.evidence_text
    if benefit.evidence_text.strip() not in section_text:
        warnings.append("benefit_evidence_not_in_section")
        return None
    if not _evidence_supports_discount_value(benefit.discount_type, benefit.discount_value, benefit.evidence_text):
        warnings.append("discount_value_not_supported_by_evidence")
        return None
    return FuelTierData(
        fuel_type=benefit.fuel_type or "ALL",
        min_performance_amount=0,
        discount_type=benefit.discount_type,
        discount_value=benefit.discount_value,
        brand_scope=(benefit.brand_scope or "all")[:32],
        min_payment_amount=benefit.min_payment_amount,
        monthly_discount_limit=benefit.monthly_discount_limit,
    )


def _evidence_supports_discount_value(discount_type: str, discount_value: Decimal, evidence_text: str) -> bool:
    evidence = str(evidence_text or "")
    normalized_value = _normalize_decimal_text(discount_value)
    if normalized_value in re.sub(r"[, ]", "", evidence):
        return True
    if discount_type == CardPolicy.DiscountType.FIXED_AMOUNT:
        return _fixed_amount_supported(discount_value, evidence)
    if discount_type == CardPolicy.DiscountType.PER_LITER:
        return re.search(rf"{re.escape(normalized_value)}\s*원", evidence) is not None
    if discount_type == CardPolicy.DiscountType.PERCENTAGE:
        return re.search(rf"{re.escape(normalized_value)}\s*%", evidence) is not None
    return False


def _fixed_amount_supported(discount_value: Decimal, evidence_text: str) -> bool:
    for match in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*만\s*원?", evidence_text):
        if _decimal_or_zero(match.group(1)) * Decimal("10000") == discount_value:
            return True
    for match in re.finditer(r"([0-9]+)\s*천\s*원?", evidence_text):
        if Decimal(match.group(1)) * Decimal("1000") == discount_value:
            return True
    return False


def _decimal_or_zero(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation:
        return Decimal("0")


def _normalize_decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(int(normalized))
    return format(normalized, "f")
