from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Final

from .llm_fuel_extraction import JsonObject, LlmFuelPayload, build_line_numbered_document
from .selenium_ingestion import ScrapedCardCandidate

# GMS (SSAFY AI 프록시) 엔드포인트
# GMS는 원래 API 경로를 그대로 뒤에 붙여 프록시합니다.
# 예) OpenAI : https://gms.ssafy.io/gmsapi/api.openai.com/v1/responses
# 예) Gemini : https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
#
# 주의: /v1beta/interactions 엔드포인트는 GMS가 지원하지 않으므로
#       표준 generateContent 엔드포인트를 사용합니다.
# 주의: 표준 urllib.request.urlopen 은 GMS 응답을 제대로 디코딩하지 못합니다.
#       반드시 requests 라이브러리를 사용하세요.
GMS_BASE_URL: Final = "https://gms.ssafy.io/gmsapi"
GMS_GENERATE_CONTENT_PATH: Final = (
    "/generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
DEFAULT_GMS_MODEL: Final = "gemini-3.5-flash"


@dataclass(frozen=True, slots=True)
class GmsClientConfig:
    api_key: str
    model: str
    base_url: str
    timeout_seconds: int

    def generate_content_url(self) -> str:
        path = GMS_GENERATE_CONTENT_PATH.format(model=self.model)
        return f"{self.base_url}{path}"


class GmsConfigurationError(RuntimeError):
    pass


class GmsRequestError(RuntimeError):
    pass


def load_gms_config_from_env() -> GmsClientConfig:
    api_key = (
        os.getenv("GMS_API_KEY", "").strip()
        or os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )
    if not api_key:
        raise GmsConfigurationError("GMS_API_KEY is required for GMS normalization.")
    timeout_seconds = int(os.getenv("GMS_TIMEOUT_SECONDS", "30") or "30")
    base_url = os.getenv("GMS_BASE_URL", "").strip() or GMS_BASE_URL
    return GmsClientConfig(
        api_key=api_key,
        model=os.getenv("GMS_MODEL", "").strip() or DEFAULT_GMS_MODEL,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )


def build_gms_normalization_prompt(candidate: ScrapedCardCandidate) -> str:
    document = build_line_numbered_document(candidate.raw_summary)
    return f"""카드 혜택 원문에서 주유/충전/주유소/LPG/전기차 충전 혜택 구간만 직접 찾아라.
앱이 미리 잘라 준 청크를 기준으로 판단하지 말고, line-numbered raw_text에서 fuel_sections를 먼저 선택하라.
'주유' 같은 짧은 제목 줄 뒤의 할인/한도/브랜드 줄은 다음 혜택 제목이 나오기 전까지 같은 주유 혜택 구간일 수 있다.
일반 가맹점/통신/커피/영화 혜택은 주유 구간의 조건이 아니라면 fuel benefit으로 추출하지 마라.
신규 회원 이벤트/웰컴 혜택 등 한시적 이벤트 할인(100% 등 비현실적 할인율)은 fuel benefit으로 추출하지 마라.
evidence_text는 선택한 라인 범위에서 그대로 복사하라.

반드시 JSON만 반환하라. benefits 항목은 category=fuel일 때만 포함하라.
discount_type은 per_liter, percentage, fixed_amount 중 하나여야 한다.
discount_value는 숫자로 반환하라.
benefits[*].evidence_section_index는 fuel_sections 배열의 0-based index다.
min_payment_amount는 건당/1회 최소 결제 금액(원), monthly_discount_limit은 월 최대 할인 한도(원)이다.

카드명: {candidate.card_name}
카드사: {candidate.issuer_name}

line-numbered raw_text:
{document.numbered_text}
"""


def normalize_card_fuel_benefit(candidate: ScrapedCardCandidate) -> JsonObject:
    """GMS(SSAFY AI 프록시)를 통해 Gemini로 카드 주유 혜택을 추출합니다."""
    try:
        import requests as _requests  # noqa: PLC0415
    except ImportError as exc:
        raise GmsConfigurationError(
            "requests 라이브러리가 필요합니다. pip install requests"
        ) from exc

    config = load_gms_config_from_env()
    prompt = build_gms_normalization_prompt(candidate)

    # Gemini generateContent 요청 포맷 (JSON Schema 강제)
    request_payload: JsonObject = {
        "contents": [
            {
                "parts": [{"text": prompt}],
                "role": "user",
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": LlmFuelPayload.model_json_schema(),
            "temperature": 0.0,
        },
    }

    url = config.generate_content_url()
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": config.api_key,
        "Authorization": f"Bearer {config.api_key}",
    }

    try:
        response = _requests.post(
            url,
            json=request_payload,
            headers=headers,
            timeout=config.timeout_seconds,
        )
    except Exception as exc:
        raise GmsRequestError(f"GMS 요청 실패: {exc}") from exc

    if not response.ok:
        raise GmsRequestError(
            f"GMS HTTP {response.status_code}: {response.text[:300]}"
        )

    try:
        response_json = response.json()
    except Exception as exc:
        raise GmsRequestError(f"GMS 응답이 JSON이 아닙니다: {exc}") from exc

    output_text = _extract_generate_content_text(response_json)

    try:
        parsed_output = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise GmsRequestError(f"GMS 모델 출력이 유효한 JSON이 아닙니다: {exc}") from exc

    if not isinstance(parsed_output, dict):
        raise GmsRequestError("GMS 응답이 JSON 객체가 아닙니다.")
    return parsed_output


def _extract_generate_content_text(response_json: JsonObject) -> str:
    """Gemini generateContent 응답에서 텍스트를 추출합니다."""
    candidates = response_json.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise GmsRequestError("GMS 응답에 candidates가 없습니다.")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise GmsRequestError("GMS candidate가 객체가 아닙니다.")
    content = candidate.get("content")
    if not isinstance(content, dict):
        raise GmsRequestError("GMS content가 객체가 아닙니다.")
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise GmsRequestError("GMS parts가 없습니다.")
    first_part = parts[0]
    if not isinstance(first_part, dict):
        raise GmsRequestError("GMS part가 객체가 아닙니다.")
    text = first_part.get("text")
    if not isinstance(text, str):
        raise GmsRequestError("GMS text 필드가 없습니다.")
    return text
