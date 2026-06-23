from __future__ import annotations

from collections.abc import Callable, Iterable
from decimal import Decimal

from django.utils import timezone

from .llm_fuel_extraction import FuelTierData, JsonObject, build_line_numbered_document, validate_llm_fuel_payload
from .models import CardBenefitTier, CardCatalog, CardPolicy
from .selenium_ingestion import (
    ScrapedCardCandidate,
    build_normalized_catalog_payload,
    normalize_candidate,
    persist_catalog_card_image,
)

FuelNormalizer = Callable[[ScrapedCardCandidate], JsonObject]


def save_ai_normalized_candidates(
    candidates: Iterable[ScrapedCardCandidate],
    source_url: str,
    normalizer: FuelNormalizer,
) -> list[CardCatalog]:
    saved: list[CardCatalog] = []
    for candidate in candidates:
        catalog_data, fallback_tier_data = normalize_candidate(candidate, source_url)
        if not catalog_data:
            continue
        validation = validate_llm_fuel_payload(
            build_line_numbered_document(candidate.raw_summary),
            normalizer(candidate),
        )
        tier_data = _tier_dict_from_validated(validation.tier_data) or fallback_tier_data
        catalog_card = _upsert_catalog_card(catalog_data)
        persist_catalog_card_image(catalog_card, candidate)
        catalog_card.normalized_data = _build_payload(
            catalog_card,
            candidate,
            source_url,
            validation.normalized_payload,
            validation.warnings,
            tier_data,
        )
        catalog_card.save()
        _save_tier(catalog_card, tier_data)
        saved.append(catalog_card)
    return saved


def _upsert_catalog_card(catalog_data: dict) -> CardCatalog:
    catalog_card = CardCatalog.objects.filter(source_url=catalog_data["source_url"]).first()
    if catalog_card is None:
        catalog_card = CardCatalog.objects.filter(
            card_name=catalog_data["card_name"],
            source_type=CardPolicy.SourceType.SELENIUM,
        ).first()
    if catalog_card is None:
        return CardCatalog(**catalog_data)
    for field_name, value in catalog_data.items():
        setattr(catalog_card, field_name, value)
    catalog_card.verification_status = CardPolicy.VerificationStatus.UNVERIFIED
    catalog_card.collected_at = timezone.now()
    return catalog_card


def _build_payload(
    catalog_card: CardCatalog,
    candidate: ScrapedCardCandidate,
    source_url: str,
    llm_payload: JsonObject,
    warnings: list[str],
    tier_data: dict | None,
) -> JsonObject:
    payload = build_normalized_catalog_payload(catalog_card, candidate, source_url, tier_data=tier_data)
    payload["provider"] = "gms_llm_fuel_extraction"
    payload["fuel_sections"] = llm_payload.get("fuel_sections", [])
    payload["benefits"] = llm_payload.get("benefits", payload["benefits"])
    payload["quality"] = llm_payload.get("quality", {})
    quality = payload["quality"]
    if isinstance(quality, dict):
        quality["warnings"] = warnings
        quality.setdefault("verification_status", CardPolicy.VerificationStatus.UNVERIFIED)
    return payload


def _tier_dict_from_validated(tier_data: FuelTierData | None) -> dict | None:
    if tier_data is None:
        return None
    return {
        "fuel_type": tier_data.fuel_type,
        "min_performance_amount": tier_data.min_performance_amount,
        "discount_type": tier_data.discount_type,
        "discount_value": tier_data.discount_value,
        "brand_scope": tier_data.brand_scope,
        "min_payment_amount": tier_data.min_payment_amount,
        "monthly_discount_limit": tier_data.monthly_discount_limit,
    }


def _save_tier(catalog_card: CardCatalog, tier_data: dict | None) -> None:
    if not tier_data or Decimal(tier_data["discount_value"]) <= 0:
        return
    CardBenefitTier.objects.update_or_create(
        card_catalog=catalog_card,
        fuel_type=tier_data["fuel_type"],
        min_performance_amount=tier_data["min_performance_amount"],
        defaults={
            "discount_type": tier_data["discount_type"],
            "discount_value": tier_data["discount_value"],
            "brand_scope": tier_data["brand_scope"],
            "min_payment_amount": tier_data["min_payment_amount"],
            "monthly_discount_limit": tier_data["monthly_discount_limit"],
        },
    )
