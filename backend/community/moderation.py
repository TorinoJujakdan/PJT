from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import requests
from django.conf import settings

from cards.gemini_client import GEMINI_BASE_URL, GEMINI_GENERATE_CONTENT_PATH

MODERATION_MESSAGE: Final = "\ubd80\uc801\uc808\ud55c \ud45c\ud604\uc774 \ud3ec\ud568\ub418\uc5b4 \uac8c\uc2dc\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4."
NON_FIELD_ERROR_KEY: Final = "non_field_errors"
DEFAULT_MODEL: Final = "gemini-3.5-flash"
LOCAL_BLOCKED_TERMS: Final = (
    "\uc2dc\ubc1c",
    "\uc528\ubc1c",
    "\uc2f8\ubc1c",
    "\uc2dc\ube68",
    "\uc528\ube68",
    "\ubcd1\uc2e0",
    "\ubcd1\uc2e0\uc0c8\ub07c",
    "\uac1c\uc0c8\ub07c",
    "\uc0c8\ub07c",
    "\uc9c0\ub784",
    "\ub2e5\uccd0",
    "\uaebc\uc838",
    "\uc880\ub9c8",
)


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

    local_violations = _detect_local_violations(fields)
    if local_violations:
        return ModerationResult(violations=local_violations, unavailable=False)

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
        "\ub2f9\uc2e0\uc740 \ud55c\uad6d\uc5b4 \ucee4\ubba4\ub2c8\ud2f0 \uac8c\uc2dc\uae00\uc758 "
        "\ubd80\uc801\uc808 \ud45c\ud604\uc744 \ud310\uc815\ud558\ub294 \uc5c4\uaca9\ud55c moderation "
        "\ubd84\ub958\uae30\uc785\ub2c8\ub2e4.\n"
        "\ubc18\ub4dc\uc2dc title\uacfc content boolean \ud0a4\ub9cc \ud3ec\ud568\ud55c JSON\uc73c\ub85c "
        "\uc751\ub2f5\ud558\uc138\uc694.\n"
        "true\ub294 \ud574\ub2f9 \ud544\ub4dc\uc5d0 \ud55c\uad6d\uc5b4 \uc695\uc124, \ube44\uc18d\uc5b4, "
        "\ubaa8\uc695, \ud610\uc624\u00b7\ucc28\ubcc4 \ud45c\ud604, \uc131\uc801 \ube44\ud558, "
        "\uacf5\uaca9\uc801\uc778 \ud45c\ud604\uc774 \ud3ec\ud568\ub418\uc5c8\uc74c\uc744 \ub73b\ud569\ub2c8\ub2e4.\n"
        "false\ub294 \uac8c\uc2dc \uac00\ub2a5\ud55c \ud45c\ud604\uc784\uc744 \ub73b\ud569\ub2c8\ub2e4.\n"
        "\uc124\uba85, \uadfc\uac70, \uc6d0\ubb38 \ubc18\ubcf5, \ucd94\uac00 \ud14d\uc2a4\ud2b8\ub294 "
        "\uc808\ub300 \ud3ec\ud568\ud558\uc9c0 \ub9c8\uc138\uc694.\n\n"
        f"\uc81c\ubaa9(title): {fields.get('title', '')}\n"
        f"\ub0b4\uc6a9(content): {fields.get('content', '')}\n"
    )


def _detect_local_violations(fields: dict[str, str]) -> dict[str, str]:
    violations: dict[str, str] = {}
    for field in ("title", "content"):
        text = fields.get(field)
        if not isinstance(text, str):
            continue
        normalized = "".join(text.lower().split())
        if any(term in normalized for term in LOCAL_BLOCKED_TERMS):
            violations[field] = MODERATION_MESSAGE
    return violations


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
