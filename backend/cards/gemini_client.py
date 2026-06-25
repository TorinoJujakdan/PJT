from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Final

from .llm_fuel_extraction import JsonObject, JsonValue, LlmFuelPayload, build_line_numbered_document
from .selenium_ingestion import ScrapedCardCandidate

logger = logging.getLogger(__name__)

GEMINI_BASE_URL: Final = "https://generativelanguage.googleapis.com"
GEMINI_GENERATE_CONTENT_PATH: Final = "/v1beta/models/{model}:generateContent"
DEFAULT_GEMINI_MODEL: Final = "gemini-3.5-flash"
DEFAULT_GEMINI_MAX_OUTPUT_TOKENS: Final = 2048
MAX_RAW_SUMMARY_LENGTH: Final = 3000
GEMINI_35_FLASH_INPUT_USD_PER_1M: Final = Decimal("1.50")
GEMINI_35_FLASH_OUTPUT_USD_PER_1M: Final = Decimal("9.00")
UNSUPPORTED_GEMINI_SCHEMA_KEYS: Final = frozenset(
    {"$defs", "$ref", "$schema", "anyOf", "default", "pattern", "title"}
)


@dataclass(frozen=True, slots=True)
class GeminiClientConfig:
    api_key: str
    model: str
    base_url: str
    timeout_seconds: int
    max_output_tokens: int

    def generate_content_url(self) -> str:
        path = GEMINI_GENERATE_CONTENT_PATH.format(model=self.model)
        return f"{self.base_url}{path}"


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiRequestError(RuntimeError):
    pass


class GeminiRateLimitError(GeminiRequestError):
    pass


def load_gemini_config_from_env() -> GeminiClientConfig:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiConfigurationError("GEMINI_API_KEY is required for Gemini normalization.")
    return GeminiClientConfig(
        api_key=api_key,
        model=os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL,
        base_url=os.getenv("GEMINI_BASE_URL", "").strip() or GEMINI_BASE_URL,
        timeout_seconds=_env_int("GEMINI_TIMEOUT_SECONDS", 30),
        max_output_tokens=_env_int("GEMINI_MAX_OUTPUT_TOKENS", DEFAULT_GEMINI_MAX_OUTPUT_TOKENS),
    )


def build_gemini_normalization_prompt(candidate: ScrapedCardCandidate) -> str:
    raw_summary = candidate.raw_summary or ""
    if len(raw_summary) > MAX_RAW_SUMMARY_LENGTH:
        logger.warning("Truncating raw_summary for card %s (%d chars)", candidate.card_name, len(raw_summary))
        raw_summary = raw_summary[:MAX_RAW_SUMMARY_LENGTH]

    document = build_line_numbered_document(raw_summary)
    return f"""You extract only card fuel benefits from a line-numbered Korean card document.

Rules:
- First select fuel-related source sections: 주유, 충전, LPG, 전기차 충전, 휘발유, 경유.
- Return only category="fuel" benefits.
- Do not treat general merchant, communication, coffee, movie, or onboarding/event discounts as fuel benefits.
- Copy evidence_text exactly from the selected line range.
- discount_type must be one of: per_liter, percentage, fixed_amount.
- discount_value must be numeric.
- benefits[*].evidence_section_index is the 0-based index into fuel_sections.
- min_payment_amount is a per-payment minimum; monthly_discount_limit is a monthly cap.
- If the source does not prove a fuel benefit, return empty fuel_sections and benefits with warnings.

Card name: {candidate.card_name}
Issuer: {candidate.issuer_name}

line-numbered raw_text:
{document.numbered_text}
"""


def normalize_card_fuel_benefit(candidate: ScrapedCardCandidate) -> JsonObject:
    raw_summary = candidate.raw_summary or ""
    if len(raw_summary.strip()) < 5:
        raise GeminiRequestError("raw_summary is too short for Gemini normalization.")

    try:
        import requests as _requests
    except ImportError as exc:
        raise GeminiConfigurationError("The requests package is required for Gemini normalization.") from exc

    config = load_gemini_config_from_env()
    request_payload = _build_request_payload(build_gemini_normalization_prompt(candidate), config)
    headers = {"Content-Type": "application/json", "x-goog-api-key": config.api_key}

    try:
        response = _requests.post(
            config.generate_content_url(),
            json=request_payload,
            headers=headers,
            timeout=config.timeout_seconds,
        )
    except _requests.RequestException as exc:
        raise GeminiRequestError(f"Gemini request failed: {exc}") from exc

    if not response.ok:
        if response.status_code == 429:
            raise GeminiRateLimitError(f"Gemini rate limit exceeded (429): {response.text[:300]}")
        raise GeminiRequestError(f"Gemini HTTP {response.status_code}: {response.text[:300]}")

    try:
        response_json = response.json()
    except ValueError as exc:
        raise GeminiRequestError(f"Gemini response is not valid JSON: {exc}") from exc

    if not isinstance(response_json, dict):
        raise GeminiRequestError("Gemini response JSON is not an object.")

    output_text = _extract_generate_content_text(response_json)
    try:
        parsed_output = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise GeminiRequestError(f"Gemini model output is not valid JSON: {exc}") from exc

    if not isinstance(parsed_output, dict):
        raise GeminiRequestError("Gemini model output JSON is not an object.")

    usage_metadata = _extract_usage_metadata(response_json)
    parsed_output["model"] = config.model
    parsed_output["usage_metadata"] = usage_metadata
    parsed_output["cost_estimate"] = estimate_gemini_cost(config.model, usage_metadata)
    return parsed_output


def estimate_gemini_cost(model: str, usage_metadata: JsonObject) -> JsonObject:
    prompt_tokens = _usage_token_count(usage_metadata, "promptTokenCount", "prompt_token_count", "input_tokens")
    candidate_tokens = _usage_token_count(
        usage_metadata,
        "candidatesTokenCount",
        "candidates_token_count",
        "output_tokens",
    )
    thinking_tokens = _usage_token_count(
        usage_metadata,
        "thoughtsTokenCount",
        "thoughts_token_count",
        "thinkingTokenCount",
        "thinking_token_count",
        "thinking_tokens",
    )
    output_tokens = candidate_tokens + thinking_tokens
    if "gemini-3.5-flash" not in model:
        return {
            "model": model,
            "input_tokens": prompt_tokens,
            "candidate_tokens": candidate_tokens,
            "thinking_tokens": thinking_tokens,
            "output_tokens": output_tokens,
            "pricing_status": "unknown_model",
        }

    input_cost = Decimal(prompt_tokens) * GEMINI_35_FLASH_INPUT_USD_PER_1M / Decimal("1000000")
    output_cost = Decimal(output_tokens) * GEMINI_35_FLASH_OUTPUT_USD_PER_1M / Decimal("1000000")
    return {
        "model": model,
        "input_tokens": prompt_tokens,
        "candidate_tokens": candidate_tokens,
        "thinking_tokens": thinking_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": _money_string(input_cost),
        "output_cost_usd": _money_string(output_cost),
        "total_cost_usd": _money_string(input_cost + output_cost),
        "pricing_basis": "Gemini API paid tier, gemini-3.5-flash standard pricing",
    }


def _build_request_payload(prompt: str, config: GeminiClientConfig) -> JsonObject:
    return {
        "contents": [{"parts": [{"text": prompt}], "role": "user"}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _build_gemini_response_schema(),
            "temperature": 0.0,
            "maxOutputTokens": config.max_output_tokens,
        },
    }


def _build_gemini_response_schema() -> JsonObject:
    pydantic_schema = LlmFuelPayload.model_json_schema()
    definitions = _schema_definitions(pydantic_schema)
    return _gemini_schema_node(pydantic_schema, definitions)


def _schema_definitions(schema: JsonObject) -> dict[str, JsonObject]:
    raw_definitions = schema.get("$defs")
    if not isinstance(raw_definitions, dict):
        return {}
    return {
        name: definition
        for name, definition in raw_definitions.items()
        if isinstance(name, str) and isinstance(definition, dict)
    }


def _gemini_schema_node(schema: JsonObject, definitions: dict[str, JsonObject]) -> JsonObject:
    ref = schema.get("$ref")
    if isinstance(ref, str):
        definition = definitions.get(ref.rsplit("/", maxsplit=1)[-1])
        if definition is None:
            return {}
        return _gemini_schema_node(definition, definitions)

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        return _gemini_any_of_node(any_of, definitions)

    converted: JsonObject = {}
    for key, value in schema.items():
        if key in UNSUPPORTED_GEMINI_SCHEMA_KEYS:
            continue
        if key == "properties" and isinstance(value, dict):
            converted[key] = _gemini_schema_properties(value, definitions)
            continue
        if key == "items" and isinstance(value, dict):
            converted[key] = _gemini_schema_node(value, definitions)
            continue
        if key == "required" and isinstance(value, list):
            converted[key] = [item for item in value if isinstance(item, str)]
            continue
        if key == "additionalProperties" and isinstance(value, bool):
            converted[key] = value
            continue
        if key in {"description", "type"} and isinstance(value, str):
            converted[key] = value
            continue
        if key == "enum" and isinstance(value, list):
            converted[key] = _json_scalar_list(value)
            continue

    return converted


def _gemini_schema_properties(
    properties: dict[str, JsonValue],
    definitions: dict[str, JsonObject],
) -> JsonObject:
    converted: JsonObject = {}
    for property_name, property_schema in properties.items():
        if isinstance(property_name, str) and isinstance(property_schema, dict):
            converted[property_name] = _gemini_schema_node(property_schema, definitions)
    return converted


def _gemini_any_of_node(options: list[JsonValue], definitions: dict[str, JsonObject]) -> JsonObject:
    converted_options = [
        _gemini_schema_node(option, definitions)
        for option in options
        if isinstance(option, dict)
    ]
    non_null_options = [
        option for option in converted_options if option.get("type") != "null"
    ]
    if not non_null_options:
        return {}

    selected = next(
        (option for option in non_null_options if option.get("type") == "number"),
        non_null_options[0],
    )
    if len(non_null_options) < len(converted_options):
        selected["nullable"] = True
    return selected


def _json_scalar_list(values: list[JsonValue]) -> list[JsonValue]:
    return [
        value
        for value in values
        if isinstance(value, str | int | float | bool) or value is None
    ]


def _extract_generate_content_text(response_json: JsonObject) -> str:
    candidates = response_json.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise GeminiRequestError("Gemini response has no candidates.")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise GeminiRequestError("Gemini candidate is not an object.")
    content = candidate.get("content")
    if not isinstance(content, dict):
        raise GeminiRequestError("Gemini content is not an object.")
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise GeminiRequestError("Gemini content has no parts.")
    first_part = parts[0]
    if not isinstance(first_part, dict):
        raise GeminiRequestError("Gemini part is not an object.")
    text = first_part.get("text")
    if not isinstance(text, str):
        raise GeminiRequestError("Gemini part text is missing.")
    return text


def _extract_usage_metadata(response_json: JsonObject) -> JsonObject:
    usage_metadata = response_json.get("usageMetadata")
    if isinstance(usage_metadata, dict):
        return usage_metadata
    snake_usage_metadata = response_json.get("usage_metadata")
    if isinstance(snake_usage_metadata, dict):
        return snake_usage_metadata
    return {}


def _usage_token_count(usage_metadata: JsonObject, *keys: str) -> int:
    for key in keys:
        raw_value = usage_metadata.get(key)
        if isinstance(raw_value, int):
            return raw_value
        if isinstance(raw_value, str):
            try:
                return int(raw_value)
            except ValueError:
                continue
    return 0


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise GeminiConfigurationError(f"{name} must be an integer.") from exc


def _money_string(value: Decimal) -> str:
    try:
        return str(value.quantize(Decimal("0.000001")).normalize())
    except InvalidOperation:
        return "0"
