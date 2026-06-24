from __future__ import annotations

from decimal import Decimal, InvalidOperation

type DiscountValueInput = str | int | float | Decimal | None

FUEL_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "주유",
    "주유소",
    "주유비",
    "충전",
    "충전소",
    "리터당",
    "LPG",
    "전기차",
    "휘발유",
    "경유",
    "fuel",
    "oil",
    "gasoline",
    "diesel",
    "liter",
    "litre",
)
MAX_REASONABLE_PERCENTAGE = Decimal("50")
MAX_REASONABLE_PER_LITER = Decimal("500")
MAX_REASONABLE_FIXED_AMOUNT = Decimal("50000")


def decimal_or_zero(value: DiscountValueInput) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (ArithmeticError, InvalidOperation, ValueError):
        return Decimal("0")


def has_fuel_context(text: str) -> bool:
    source_text = str(text or "")
    normalized_text = source_text.lower()
    return any(keyword in source_text or keyword.lower() in normalized_text for keyword in FUEL_CONTEXT_KEYWORDS)


def is_suspicious_fuel_discount(discount_type: str, discount_value: Decimal) -> bool:
    value = decimal_or_zero(discount_value)
    if value <= 0:
        return True
    if discount_type == "percentage":
        return value > MAX_REASONABLE_PERCENTAGE
    if discount_type == "per_liter":
        return value > MAX_REASONABLE_PER_LITER
    if discount_type == "fixed_amount":
        return value > MAX_REASONABLE_FIXED_AMOUNT
    return True


def is_usable_fuel_benefit(discount_type: str, discount_value: Decimal, evidence_text: str = "") -> bool:
    if evidence_text and not has_fuel_context(evidence_text):
        return False
    return not is_suspicious_fuel_discount(discount_type, discount_value)
