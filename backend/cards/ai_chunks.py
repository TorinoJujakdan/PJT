from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Sequence

MAX_CHUNK_CHARS = 1600

FUEL_KEYWORDS = (
    "주유",
    "주유소",
    "충전",
    "충전소",
    "LPG",
    "휘발유",
    "경유",
    "리터당",
    "fuel",
    "gas",
)
LIMIT_KEYWORDS = (
    "한도",
    "월",
    "월간",
    "최대",
    "전월",
    "실적",
    "건당",
    "1회",
    "회당",
    "이상",
)
EXCLUSION_KEYWORDS = (
    "제외",
    "미포함",
    "제한",
    "불가",
    "상품권",
    "일부",
)


@dataclass(frozen=True, slots=True)
class CardTextChunk:
    name: str
    text: str


def compute_raw_hash(raw_text: str) -> str:
    normalized_text = "\n".join(line.rstrip() for line in str(raw_text or "").strip().splitlines())
    digest = sha256(normalized_text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_chunks(raw_text: str) -> list[CardTextChunk]:
    lines = clean_lines(raw_text)
    chunks = [
        CardTextChunk("identity", trim_chunk("\n".join(lines[:8]))),
        CardTextChunk("fuel_benefit", trim_chunk(select_keyword_lines(lines, FUEL_KEYWORDS))),
        CardTextChunk("limits", trim_chunk(select_keyword_lines(lines, LIMIT_KEYWORDS))),
        CardTextChunk("exclusions", trim_chunk(select_keyword_lines(lines, EXCLUSION_KEYWORDS))),
    ]
    return [chunk for chunk in chunks if chunk.text]


def trim_chunk(text: str) -> str:
    normalized = str(text or "").strip()
    if len(normalized) <= MAX_CHUNK_CHARS:
        return normalized
    return normalized[:MAX_CHUNK_CHARS].rstrip()


def clean_lines(raw_text: str) -> list[str]:
    return [line.strip() for line in str(raw_text or "").splitlines() if line.strip()]


def select_keyword_lines(lines: Sequence[str], keywords: Sequence[str]) -> str:
    selected: list[str] = []
    for index, line in enumerate(lines):
        if contains_keyword(line, keywords):
            previous_line = lines[index - 1] if index > 0 else ""
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            selected.extend(part for part in (previous_line, line, next_line) if part)
    return "\n".join(dict.fromkeys(selected))


def contains_keyword(line: str, keywords: Sequence[str]) -> bool:
    lower_line = line.lower()
    return any(keyword.lower() in lower_line for keyword in keywords)
