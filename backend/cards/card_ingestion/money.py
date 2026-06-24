from __future__ import annotations

import re
from decimal import Decimal

MAN = "\ub9cc"
THOUSAND = "\ucc9c"
WON = "\uc6d0"

MONEY_PATTERN = (
    r"(?P<amount>"
    rf"[0-9]+(?:\.[0-9]+)?\s*(?:{MAN}{WON}|{MAN})"
    rf"|[0-9]+\s*(?:{THOUSAND}{WON}|{THOUSAND})"
    rf"|[0-9][0-9,]*\s*(?:{WON}|won)"
    r"|[0-9][0-9,]*"
    r")"
)

def parse_korean_money_amount(value):
    text = " ".join(str(value or "").split())
    if not text:
        return None

    total = Decimal("0")
    man_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:만|만원)", text)
    if man_match:
        total += Decimal(man_match.group(1)) * Decimal("10000")

    thousand_match = re.search(r"([0-9]+)\s*(?:천|천원)", text)
    if thousand_match:
        total += Decimal(thousand_match.group(1)) * Decimal("1000")

    if total:
        return int(total)

    won_match = re.search(r"([0-9][0-9,]*)\s*(?:원|won)?", text, flags=re.IGNORECASE)
    if won_match:
        return int(won_match.group(1).replace(",", ""))

    return None


def extract_first_amount(pattern, text, skip_if_contains=None, skip_before_contains=None):
    skip_tokens = skip_if_contains or []
    skip_before_tokens = skip_before_contains or []
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        snippet = match.group(0)
        if any(token in snippet for token in skip_tokens):
            continue
        before = text[max(0, match.start() - 40) : match.start()]
        if any(token in before for token in skip_before_tokens):
            continue
        amount = parse_korean_money_amount(match.group("amount"))
        if amount is not None:
            return amount
    return None


