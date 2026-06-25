from __future__ import annotations

from dataclasses import dataclass
from typing import Final

CANONICAL_ALL_SCOPE: Final = "all"
FOUR_MAJOR_STATION_SCOPE: Final = "SK,GS,S-OIL,HD\ud604\ub300\uc624\uc77c\ubc45\ud06c"

_ALL_SCOPE_TOKENS: Final = frozenset(
    {
        "all",
        "all fuel",
        "ALL",
        "\ubaa8\ub4e0 \uc8fc\uc720\uc18c",
        "\uc804\uad6d \uc8fc\uc720\uc18c",
        "\uc804\uad6d \ubaa8\ub4e0 \uc8fc\uc720\uc18c",
        "\uad6d\ub0b4 \uc8fc\uc720\uc18c",
        "\uad6d\ub0b4 \ubaa8\ub4e0 \uc8fc\uc720\uc18c",
        "\uc8fc\uc720\uc18c \uc804\uccb4",
        "\uc804\uc8fc\uc720\uc18c",
        "\ubaa8\ub4e0 \uc8fc\uc720\uc18c/\ucda9\uc804\uc18c",
    }
)
_FOUR_MAJOR_TOKENS: Final = frozenset({"4\ub300 \uc8fc\uc720\uc18c", "4\ub300\uc8fc\uc720\uc18c", "4\ub300 \uc815\uc720", "4\ub300\uc815\uc720"})
_BRAND_TOKENS: Final = (
    ("HD\ud604\ub300\uc624\uc77c\ubc45\ud06c", ("HD\ud604\ub300\uc624\uc77c\ubc45\ud06c", "\ud604\ub300\uc624\uc77c\ubc45\ud06c", "OILBANK", "HD HYUNDAI")),
    ("GS", ("GS\uce7c\ud14d\uc2a4", "GS CALTEX", "GS\uc8fc\uc720", "GS")),
    ("SK", ("SK\uc5d0\ub108\uc9c0", "SK\uc8fc\uc720", "SK ENERGY", "SK")),
    ("S-OIL", ("S-OIL", "\uc5d0\uc4f0\uc624\uc77c", "\uc5d0\uc2a4\uc624\uc77c", "S OIL")),
    ("E1", ("E1",)),
)
_STATION_BRAND_ALIASES: Final = {
    "HD_HYUNDAI": "HD\ud604\ub300\uc624\uc77c\ubc45\ud06c",
    "S_OIL": "S-OIL",
}


@dataclass(frozen=True, slots=True)
class NormalizedBrandScope:
    scope: str
    inferred: bool
    reason: str


def normalize_brand_scope(value: str | None) -> NormalizedBrandScope:
    source = str(value or "").strip()
    if not source:
        return NormalizedBrandScope(CANONICAL_ALL_SCOPE, False, "empty_as_all")

    if source in _ALL_SCOPE_TOKENS or source.lower() == CANONICAL_ALL_SCOPE:
        return NormalizedBrandScope(CANONICAL_ALL_SCOPE, False, "canonical_all")

    if any(token in source for token in _FOUR_MAJOR_TOKENS):
        return NormalizedBrandScope(FOUR_MAJOR_STATION_SCOPE, True, "expanded_four_major_stations")

    normalized_source = source.upper()
    matches: list[str] = []
    for brand, tokens in _BRAND_TOKENS:
        if any(token.upper() in normalized_source for token in tokens):
            matches.append(brand)

    if matches:
        deduped = list(dict.fromkeys(matches))
        return NormalizedBrandScope(",".join(deduped), False, "matched_brand_tokens")

    return NormalizedBrandScope(source[:32], True, "unmapped_original_scope")


def normalize_station_brand(value: str | None) -> str:
    source = str(value or "").strip()
    if not source:
        return ""
    if source in _STATION_BRAND_ALIASES:
        return _STATION_BRAND_ALIASES[source]
    normalized = normalize_brand_scope(source)
    return normalized.scope
