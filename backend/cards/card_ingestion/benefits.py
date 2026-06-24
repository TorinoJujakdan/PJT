from __future__ import annotations

import re
from dataclasses import replace
from decimal import Decimal

from cards.models import CardPolicy

from .money import MONEY_PATTERN, extract_first_amount

def infer_brand_scope(text):
    source_text = str(text or "")
    normalized = source_text.upper()
    all_patterns = ["모든 주유", "전국 주유", "모든 충전", "주유 충전", "전 가맹점", "all fuel"]
    if any(pattern in source_text.lower() for pattern in all_patterns):
        return "all"

    brand_patterns = [
        ("GS", ["GS칼텍스", "GS CALTEX", "GS주유"]),
        ("SK", ["SK에너지", "SK주유", "SK ENERGY"]),
        ("S-OIL", ["S-OIL", "에쓰오일", "에스오일"]),
        ("HD현대오일뱅크", ["현대오일뱅크", "HD현대오일뱅크", "OILBANK"]),
        ("E1", ["E1"]),
        ("SK LPG", ["SK가스", "SK GAS"]),
    ]
    matches = []
    for brand, tokens in brand_patterns:
        if any(token.upper() in normalized for token in tokens):
            matches.append(brand)

    if not matches:
        return "all"

    return ",".join(matches)[:32]


def infer_fuel_type(text):
    """Infer whether a benefit is EV-only or applies to regular fuel."""
    source_text = str(text or "")
    normalized = source_text.upper()
    conventional_tokens = (
        "FUEL",
        "GASOLINE",
        "DIESEL",
        "OIL",
        "LPG",
        "주유",
        "주유비",
        "휘발유",
        "경유",
        "리터",
    )
    if any(token in source_text or token in normalized for token in conventional_tokens):
        return "ALL"

    ev_tokens = (
        "EV",
        "ELECTRIC",
        "전기차",
        "전기",
        "충전",
        "충전요금",
    )
    if any(token in source_text or token in normalized for token in ev_tokens):
        return "EV"

    return "ALL"


def parse_benefit_constraints(text):
    normalized = " ".join(str(text or "").split())
    min_payment_amount = extract_first_amount(
        rf"(?:건당|1회당|결제금액|이용금액|주유금액)[^.\n]{{0,30}}?{MONEY_PATTERN}\s*(?:이상|over)",
        normalized,
        skip_if_contains=["전월", "직전", "실적", "합계"],
        skip_before_contains=["전월", "직전", "실적", "합계"],
    )
    if min_payment_amount is None:
        min_payment_amount = extract_first_amount(
            rf"{MONEY_PATTERN}\s*(?:이상|over)[^.\n]{{0,30}}?(?:결제|이용|주유)",
            normalized,
            skip_if_contains=["전월", "직전", "실적", "합계"],
            skip_before_contains=["전월", "직전", "실적", "합계"],
        )

    max_discount_amount = extract_first_amount(
        rf"(?:건당|1회당)[^.\n]{{0,30}}?(?:최대|한도)\s*{MONEY_PATTERN}",
        normalized,
    )
    if max_discount_amount is None:
        max_discount_amount = extract_first_amount(
            rf"(?:건당|1회당)[^.\n]{{0,30}}?{MONEY_PATTERN}\s*(?:까지|한도)",
            normalized,
            skip_if_contains=["이상", "over"],
        )

    monthly_discount_limit = extract_first_amount(
        rf"(?:월간|월)[^.\n]{{0,35}}?(?:최대|통합|할인한도|한도)[^.\n]{{0,15}}?{MONEY_PATTERN}",
        normalized,
        skip_if_contains=["전월", "실적", "이상"],
    )
    if monthly_discount_limit is None:
        monthly_discount_limit = extract_first_amount(
            rf"{MONEY_PATTERN}\s*(?:월간|월)[^.\n]{{0,20}}?(?:통합)?\s*(?:할인)?한도",
            normalized,
            skip_if_contains=["전월", "실적", "이상"],
        )

    monthly_remaining_discount = extract_first_amount(
        rf"(?:잔여월)[^.\n]{{0,20}}?(?:잔여|잔액|남은)[^.\n]{{0,15}}?{MONEY_PATTERN}",
        normalized,
    )

    return {
        "min_payment_amount": min_payment_amount,
        "max_discount_amount": max_discount_amount,
        "monthly_discount_limit": monthly_discount_limit,
        "monthly_remaining_discount": monthly_remaining_discount,
    }


def summarize_detail_text(text, max_length=2000):
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    focused_lines = [
        line
        for line in lines
        if any(
            token in line
            for token in [
                "주유",
                "충전",
                "리터",
                "LPG",
                "전기차",
                "할인",
                "캐시백",
                "한도",
                "건당",
                "회",
                "이상",
            ]
        )
    ]
    summary = " ".join(focused_lines or lines)
    return summary[:max_length]


def summarize_fuel_benefit_text(text, max_length=1000):
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    fuel_tokens = ["주유", "충전", "리터", "LPG", "전기차", "휘발유", "경유"]
    context_tokens = ["할인", "캐시백", "한도", "건당", "1회", "회당", "이상", "원"]
    selected = []

    for index, line in enumerate(lines):
        if not any(token in line for token in fuel_tokens):
            continue
        selected.append(line)
        for nearby in lines[index + 1 : index + 4]:
            if any(token in nearby for token in context_tokens):
                selected.append(nearby)

    return " ".join(dict.fromkeys(selected))[:max_length]


def enrich_candidate_from_detail_text(candidate, detail_text, source_url=None, source_title=""):
    raw_summary = summarize_detail_text(detail_text)
    fuel_summary = summarize_fuel_benefit_text(detail_text) or raw_summary
    discount_type, discount_value = parse_fuel_discount(fuel_summary)
    constraints = parse_benefit_constraints(fuel_summary)
    found_fields = sum(1 for value in constraints.values() if value is not None)

    if discount_value <= 0:
        discount_type = candidate.discount_type
        discount_value = candidate.discount_value
    else:
        found_fields += 1

    brand_scope = infer_brand_scope(fuel_summary)
    if brand_scope != "all":
        found_fields += 1
    else:
        brand_scope = candidate.brand_scope or "all"

    base_confidence = candidate.confidence or Decimal("0.60")
    penalty = Decimal("0.00")

    if discount_type == CardPolicy.DiscountType.PER_LITER:
        if discount_value > Decimal("500") or discount_value < Decimal("20"):
            discount_type = candidate.discount_type
            discount_value = candidate.discount_value
            penalty += Decimal("0.35")
    elif discount_type == CardPolicy.DiscountType.PERCENTAGE:
        if discount_value > Decimal("50") or discount_value < Decimal("1"):
            discount_type = candidate.discount_type
            discount_value = candidate.discount_value
            penalty += Decimal("0.30")

    non_fuel_tokens = ["영화", "커피", "극장", "스타벅스"]
    if any(token in fuel_summary for token in non_fuel_tokens):
        penalty += Decimal("0.05")

    confidence = base_confidence + (Decimal("0.04") * Decimal(found_fields)) - penalty
    if found_fields == 0:
        confidence = min(base_confidence, Decimal("0.60")) - penalty

    confidence = max(Decimal("0.00"), min(Decimal("0.95"), confidence))

    return replace(
        candidate,
        discount_type=discount_type,
        discount_value=discount_value,
        brand_scope=brand_scope,
        min_payment_amount=constraints["min_payment_amount"],
        max_discount_amount=constraints["max_discount_amount"],
        monthly_discount_limit=constraints["monthly_discount_limit"],
        monthly_remaining_discount=constraints["monthly_remaining_discount"],
        source_url=source_url or candidate.source_url,
        source_title=(source_title or candidate.source_title or candidate.card_name)[:255],
        raw_summary=raw_summary or candidate.raw_summary,
        confidence=confidence.quantize(Decimal("0.01")),
    )


def parse_discount(summary):
    per_liter_match = re.search(r"(?:리터|L)\s*(?:당)?[^0-9]{0,12}([0-9,]+)\s*(?:원|won)", summary, flags=re.IGNORECASE)
    if per_liter_match:
        return CardPolicy.DiscountType.PER_LITER, Decimal(per_liter_match.group(1).replace(",", ""))

    percentage_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", summary)
    if percentage_match:
        return CardPolicy.DiscountType.PERCENTAGE, Decimal(percentage_match.group(1))

    fixed_match = re.search(r"([0-9,]+)\s*(?:원|won)\s*(?:청구)?\s*할인", summary, flags=re.IGNORECASE)
    if fixed_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(fixed_match.group(1).replace(",", ""))

    korean_thousand_match = re.search(r"([0-9]+)\s*천원\s*(?:청구)?\s*할인", summary)
    if korean_thousand_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(korean_thousand_match.group(1)) * Decimal("1000")

    return CardPolicy.DiscountType.PER_LITER, Decimal("0")


def parse_fuel_discount(summary):
    fuel_prefix = r"(?:주유|충전|주유비|LPG|전기차|휘발유|경유)"
    has_fuel_context = re.search(fuel_prefix, summary, flags=re.IGNORECASE)
    if not has_fuel_context:
        return CardPolicy.DiscountType.PER_LITER, Decimal("0")

    per_liter_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?(?:리터|L)\s*(?:당)?[^0-9]{{0,12}}([0-9,]+)\s*(?:원|won)", summary, flags=re.IGNORECASE)
    if per_liter_match:
        return CardPolicy.DiscountType.PER_LITER, Decimal(per_liter_match.group(1).replace(",", ""))

    per_liter_match = re.search(rf"(?:리터|L)\s*(?:당)?[^0-9]{{0,12}}([0-9,]+)\s*(?:원|won)?[^.\n]{{0,30}}?{fuel_prefix}", summary, flags=re.IGNORECASE)
    if per_liter_match:
        return CardPolicy.DiscountType.PER_LITER, Decimal(per_liter_match.group(1).replace(",", ""))

    per_liter_match = re.search(rf"([0-9,]+)\s*(?:원|won)\s*/?\s*(?:L|리터)[^.\n]{{0,30}}?{fuel_prefix}", summary, flags=re.IGNORECASE)
    if per_liter_match:
        return CardPolicy.DiscountType.PER_LITER, Decimal(per_liter_match.group(1).replace(",", ""))

    bare_per_liter_match = re.search(rf"{fuel_prefix}\s+([0-9,]{{2,4}})(?:\s|$)", summary, flags=re.IGNORECASE)
    if bare_per_liter_match:
        return CardPolicy.DiscountType.PER_LITER, Decimal(bare_per_liter_match.group(1).replace(",", ""))

    percentage_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?([0-9]+(?:\.[0-9]+)?)\s*%", summary)
    if percentage_match:
        return CardPolicy.DiscountType.PERCENTAGE, Decimal(percentage_match.group(1))

    percentage_match = re.search(rf"([0-9]+(?:\.[0-9]+)?)\s*%[^.\n]{{0,50}}?{fuel_prefix}", summary)
    if percentage_match:
        return CardPolicy.DiscountType.PERCENTAGE, Decimal(percentage_match.group(1))

    fixed_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?([0-9,]+)\s*(?:원|won)\s*(?:청구)?\s*할인", summary, flags=re.IGNORECASE)
    if fixed_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(fixed_match.group(1).replace(",", ""))

    korean_thousand_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?([0-9]+)\s*천원\s*(?:청구)?\s*할인", summary)
    if korean_thousand_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(korean_thousand_match.group(1)) * Decimal("1000")

    fixed_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?([0-9]+)\s*천\s*(?:원)?\s*(?:청구)?\s*할인", summary)
    if fixed_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(fixed_match.group(1)) * Decimal("1000")

    return CardPolicy.DiscountType.PER_LITER, Decimal("0")


