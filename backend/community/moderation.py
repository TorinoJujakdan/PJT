from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import requests
from django.conf import settings

from cards.gemini_client import GEMINI_BASE_URL, GEMINI_GENERATE_CONTENT_PATH

MODERATION_MESSAGE: Final = "\ubd80\uc801\uc808\ud55c \ud45c\ud604\uc774 \ud3ec\ud568\ub418\uc5b4 \uac8c\uc2dc\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4."
NON_FIELD_ERROR_KEY: Final = "non_field_errors"
DEFAULT_MODEL: Final = "gemini-3.5-flash"


@dataclass(frozen=True, slots=True)
class ModerationResult:
    violations: dict[str, str]
    unavailable: bool = False


class ModerationUnavailable(RuntimeError):
    pass


def moderate_post_fields(fields: dict[str, str]) -> ModerationResult:
    title = fields.get("title")
    content = fields.get("content")
    if title is None and content is None:
        return ModerationResult(violations={})

    api_key = getattr(settings, "COMMUNITY_MODERATION_API_KEY", "").strip()
    if not api_key:
        return _handle_unavailable()

    payload = _build_request_payload(fields)
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    base_url = getattr(settings, "COMMUNITY_MODERATION_BASE_URL", GEMINI_BASE_URL)
    model = getattr(settings, "COMMUNITY_MODERATION_MODEL", DEFAULT_MODEL)
    timeout_seconds = getattr(settings, "COMMUNITY_MODERATION_TIMEOUT_SECONDS", 10)
    url = f"{base_url}{GEMINI_GENERATE_CONTENT_PATH.format(model=model)}"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
        data = response.json()
        verdict = _extract_verdict(data)
    except Exception:
        return _handle_unavailable()

    violations: dict[str, str] = {}
    if verdict.get("title") is True:
        violations["title"] = MODERATION_MESSAGE
    if verdict.get("content") is True:
        violations["content"] = MODERATION_MESSAGE
    return ModerationResult(violations=violations, unavailable=False)


def _handle_unavailable() -> ModerationResult:
    fail_closed = getattr(settings, "COMMUNITY_MODERATION_FAIL_CLOSED", not settings.DEBUG)
    if fail_closed:
        return ModerationResult(violations={NON_FIELD_ERROR_KEY: MODERATION_MESSAGE}, unavailable=True)
    return ModerationResult(violations={}, unavailable=True)


def _build_request_payload(fields: dict[str, str]) -> dict[str, Any]:
    prompt = _build_prompt(fields)
    return {
        "contents": [{"parts": [{"text": prompt}], "role": "user"}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "BOOLEAN"},
                    "content": {"type": "BOOLEAN"},
                },
                "required": ["title", "content"],
                "additionalProperties": False,
            },
            "temperature": 0.0,
        },
    }


def _build_prompt(fields: dict[str, str]) -> str:
    return (
        "You are a strict moderation classifier for community posts.\n"
        "Return ONLY JSON with boolean keys title and content.\n"
        "True means the field contains profanity, abuse, slurs, or clearly offensive language.\n"
        "False means it is acceptable.\n"
        "Do not include explanations or repeat the text.\n\n"
        f"title: {fields.get('title', '')}\n"
        f"content: {fields.get('content', '')}\n"
    )


def _extract_verdict(data: dict[str, Any]) -> dict[str, bool]:
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ModerationUnavailable("Gemini response missing candidates.")

    first = candidates[0]
    if not isinstance(first, dict):
        raise ModerationUnavailable("Gemini response candidate malformed.")

    content = first.get("content")
    if not isinstance(content, dict):
        raise ModerationUnavailable("Gemini response content malformed.")

    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ModerationUnavailable("Gemini response parts malformed.")

    text_value = parts[0].get("text") if isinstance(parts[0], dict) else None
    if not isinstance(text_value, str):
        raise ModerationUnavailable("Gemini response text missing.")

    import json

    parsed = json.loads(text_value)
    if not isinstance(parsed, dict):
        raise ModerationUnavailable("Gemini response JSON malformed.")

    return {
        "title": bool(parsed.get("title")),
        "content": bool(parsed.get("content")),
    }
