from cards.benefit_safety import decimal_or_zero, is_suspicious_fuel_discount
from cards.brand_scope import normalize_brand_scope, normalize_station_brand
from cards.models import CardPolicy

CATALOG_ALL_FUEL_TYPE = "all"

def get_card_value(card, field_name, default=None):
    if isinstance(card, dict):
        return card.get(field_name, default)
    return getattr(card, field_name, default)


def card_can_affect_recommendation(card):
    verification_status = get_card_value(card, "verification_status", CardPolicy.VerificationStatus.USER_CONFIRMED)
    return verification_status in {
        CardPolicy.VerificationStatus.USER_CONFIRMED,
        CardPolicy.VerificationStatus.ADMIN_VERIFIED,
    }


def brand_matches(brand_scope, station_brand):
    normalized_scope = normalize_brand_scope(str(brand_scope or "")).scope
    if normalized_scope == "all":
        return True

    normalized_station_brand = normalize_station_brand(str(station_brand or "")).lower()
    scopes = [item.strip().lower() for item in normalized_scope.split(",")]
    return normalized_station_brand in scopes


def serialize_selected_card(card, calculated_discount_amount):
    card_id = get_card_value(card, "id", None) or get_card_value(card, "card_id", None)
    card_image_url = get_card_value(card, "card_image_url", None) or None
    return {
        "card_id": str(card_id) if card_id is not None else "",
        "card_name": get_card_value(card, "card_name", ""),
        "issuer_name": get_card_value(card, "issuer_name", ""),
        "discount_type": get_card_value(card, "discount_type", ""),
        "discount_value": float(get_card_value(card, "discount_value", 0)),
        "calculated_discount_amount": calculated_discount_amount,
        "card_image_url": card_image_url,
        "source_type": get_card_value(card, "source_type", CardPolicy.SourceType.MANUAL),
        "verification_status": get_card_value(
            card,
            "verification_status",
            CardPolicy.VerificationStatus.USER_CONFIRMED,
        ),
    }


def normalize_catalog_fuel_type(value):
    return str(value or "").strip().lower()


def catalog_tier_matches_fuel_type(tier, fuel_type):
    tier_fuel_type = normalize_catalog_fuel_type(tier.fuel_type)
    requested_fuel_type = normalize_catalog_fuel_type(fuel_type)
    return tier_fuel_type in {CATALOG_ALL_FUEL_TYPE, requested_fuel_type}


def catalog_tier_matches_performance(tier, previous_month_spending):
    if previous_month_spending is None:
        return False

    spending = int(previous_month_spending)
    if int(tier.min_performance_amount or 0) > spending:
        return False
    max_performance_amount = tier.max_performance_amount
    return max_performance_amount is None or spending <= int(max_performance_amount)


def get_catalog_benefit_tiers(card):
    catalog = get_card_value(card, "linked_catalog", None)
    if catalog is None:
        return None

    benefit_tiers = getattr(catalog, "benefit_tiers", None)
    if benefit_tiers is None:
        return None

    return list(benefit_tiers.all())


def resolve_catalog_benefit_tier(card, fuel_type, benefit_tiers):
    previous_month_spending = get_card_value(card, "previous_month_spending", None)
    requested_fuel_type = normalize_catalog_fuel_type(fuel_type)
    matching_tiers = [
        tier
        for tier in benefit_tiers
        if catalog_tier_matches_fuel_type(tier, requested_fuel_type)
        and catalog_tier_matches_performance(tier, previous_month_spending)
    ]
    if not matching_tiers:
        return None

    return sorted(
        matching_tiers,
        key=lambda tier: (
            normalize_catalog_fuel_type(tier.fuel_type) == requested_fuel_type,
            int(tier.min_performance_amount or 0),
            tier.id,
        ),
        reverse=True,
    )[0]


def build_effective_card_for_fuel_type(card, fuel_type):
    benefit_tiers = get_catalog_benefit_tiers(card)
    if benefit_tiers is None:
        return card
    if not benefit_tiers:
        return card

    tier = resolve_catalog_benefit_tier(card, fuel_type, benefit_tiers)
    if tier is None:
        return None

    return {
        "id": get_card_value(card, "id", None),
        "card_id": get_card_value(card, "card_id", None),
        "card_name": get_card_value(card, "card_name", ""),
        "issuer_name": get_card_value(card, "issuer_name", ""),
        "discount_type": tier.discount_type,
        "discount_value": tier.discount_value,
        "brand_scope": tier.brand_scope,
        "min_payment_amount": tier.min_payment_amount,
        "max_discount_amount": get_card_value(card, "max_discount_amount", None),
        "monthly_discount_limit": tier.monthly_discount_limit,
        "monthly_remaining_discount": get_card_value(card, "monthly_remaining_discount", None),
        "source_type": get_card_value(card, "source_type", CardPolicy.SourceType.MANUAL),
        "verification_status": get_card_value(
            card,
            "verification_status",
            CardPolicy.VerificationStatus.USER_CONFIRMED,
        ),
        "card_image_url": get_card_value(card, "card_image_url", None),
    }


def calculate_card_discount(candidate, refuel_cost, target_liters, user_cards):
    best_discount = 0
    selected_card = None

    for card in user_cards or []:
        if not card_can_affect_recommendation(card):
            continue
        effective_card = build_effective_card_for_fuel_type(card, candidate.fuel_type)
        if effective_card is None:
            continue
        if not brand_matches(get_card_value(effective_card, "brand_scope", "all"), candidate.station.brand):
            continue

        min_payment_amount = get_card_value(effective_card, "min_payment_amount", None)
        if min_payment_amount is not None and int(min_payment_amount) > refuel_cost:
            continue

        discount_type = get_card_value(effective_card, "discount_type")
        discount_decimal = decimal_or_zero(get_card_value(effective_card, "discount_value", 0))
        if is_suspicious_fuel_discount(discount_type, discount_decimal):
            continue
        discount_value = float(discount_decimal)
        if discount_type == CardPolicy.DiscountType.PER_LITER:
            raw_discount = discount_value * float(target_liters)
        elif discount_type == CardPolicy.DiscountType.PERCENTAGE:
            raw_discount = refuel_cost * discount_value / 100
        elif discount_type == CardPolicy.DiscountType.FIXED_AMOUNT:
            raw_discount = discount_value
        else:
            raw_discount = 0

        discount = round(raw_discount)
        max_discount_amount = get_card_value(effective_card, "max_discount_amount", None)
        monthly_discount_limit = get_card_value(effective_card, "monthly_discount_limit", None)
        monthly_remaining_discount = get_card_value(effective_card, "monthly_remaining_discount", None)
        if max_discount_amount is not None:
            discount = min(discount, int(max_discount_amount))
        if monthly_discount_limit is not None:
            discount = min(discount, int(monthly_discount_limit))
        if monthly_remaining_discount is not None:
            discount = min(discount, int(monthly_remaining_discount))
        discount = max(discount, 0)

        if discount > best_discount:
            best_discount = discount
            selected_card = serialize_selected_card(effective_card, discount)

    return best_discount, selected_card
