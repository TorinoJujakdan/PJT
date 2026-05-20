from dataclasses import dataclass
from decimal import Decimal
from math import asin, cos, radians, sin, sqrt
from typing import Any, Optional

from django.db.models import OuterRef, Subquery

from cards.models import CardPolicy

from .models import FuelPrice, GasStation


EARTH_RADIUS_KM = 6371.0
DEFAULT_RADIUS_KM = 15.0
MAX_RADIUS_KM = 30.0


@dataclass(frozen=True)
class StationCandidate:
    station: GasStation
    distance_km: float
    fuel_type: str
    fuel_price_per_liter: int


@dataclass(frozen=True)
class FuelPriceRecommendation:
    candidate: StationCandidate
    target_liters: float
    refuel_cost: int
    card_discount_amount: int
    travel_cost: int
    effective_total_cost: int
    estimated_saving: int
    selected_card: Optional[dict[str, Any]]
    reason: str


def haversine_distance_km(lat1, lon1, lat2, lon2):
    lat1_rad = radians(float(lat1))
    lon1_rad = radians(float(lon1))
    lat2_rad = radians(float(lat2))
    lon2_rad = radians(float(lon2))

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return EARTH_RADIUS_KM * c


def calculate_bounding_box(latitude, longitude, radius_km):
    latitude = float(latitude)
    longitude = float(longitude)
    radius_km = float(radius_km)

    lat_delta = radius_km / 111.0
    lon_scale = cos(radians(latitude))
    lon_delta = radius_km / (111.0 * lon_scale) if abs(lon_scale) > 0.000001 else 180.0

    return {
        "min_latitude": Decimal(str(latitude - lat_delta)),
        "max_latitude": Decimal(str(latitude + lat_delta)),
        "min_longitude": Decimal(str(longitude - lon_delta)),
        "max_longitude": Decimal(str(longitude + lon_delta)),
    }


def normalize_radius_km(radius_km):
    if radius_km is None:
        return DEFAULT_RADIUS_KM

    radius = float(radius_km)
    if radius < 1 or radius > MAX_RADIUS_KM:
        raise ValueError("INVALID_RADIUS")
    return radius


def get_station_candidates(location, radius_km, fuel_type):
    radius = normalize_radius_km(radius_km)
    latitude = float(location["latitude"])
    longitude = float(location["longitude"])
    bbox = calculate_bounding_box(latitude, longitude, radius)

    latest_price = (
        FuelPrice.objects.filter(station=OuterRef("pk"), fuel_type=fuel_type)
        .order_by("-collected_at", "-id")
        .values("price_per_liter")[:1]
    )

    queryset = (
        GasStation.objects.filter(
            latitude__gte=bbox["min_latitude"],
            latitude__lte=bbox["max_latitude"],
            longitude__gte=bbox["min_longitude"],
            longitude__lte=bbox["max_longitude"],
        )
        .annotate(fuel_price_per_liter=Subquery(latest_price))
        .exclude(fuel_price_per_liter__isnull=True)
    )

    candidates = []
    for station in queryset:
        distance_km = haversine_distance_km(latitude, longitude, station.latitude, station.longitude)
        if distance_km <= radius:
            candidates.append(
                StationCandidate(
                    station=station,
                    distance_km=round(distance_km, 2),
                    fuel_type=fuel_type,
                    fuel_price_per_liter=int(station.fuel_price_per_liter),
                )
            )

    return sorted(candidates, key=lambda item: (item.distance_km, item.fuel_price_per_liter, item.station.id))


def calculate_refuel_cost(fuel_price_per_liter, target_liters):
    return round(int(fuel_price_per_liter) * float(target_liters))


def calculate_travel_cost(distance_km, fuel_efficiency_kmpl, fuel_price_per_liter, travel_mode):
    distance_multiplier = 1 if travel_mode == "one_way" else 2
    travel_distance_km = float(distance_km) * distance_multiplier
    travel_fuel_liters = travel_distance_km / float(fuel_efficiency_kmpl)
    return round(travel_fuel_liters * int(fuel_price_per_liter))


def get_card_value(card, field_name, default=None):
    if isinstance(card, dict):
        return card.get(field_name, default)
    return getattr(card, field_name, default)


def card_can_affect_recommendation(card):
    source_type = get_card_value(card, "source_type", CardPolicy.SourceType.MANUAL)
    verification_status = get_card_value(card, "verification_status", CardPolicy.VerificationStatus.USER_CONFIRMED)
    return source_type == CardPolicy.SourceType.MANUAL or verification_status in {
        CardPolicy.VerificationStatus.USER_CONFIRMED,
        CardPolicy.VerificationStatus.ADMIN_VERIFIED,
    }


def brand_matches(brand_scope, station_brand):
    if not brand_scope or str(brand_scope).lower() == "all":
        return True

    normalized_station_brand = str(station_brand).strip().lower()
    scopes = [item.strip().lower() for item in str(brand_scope).split(",")]
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


def calculate_card_discount(station, refuel_cost, target_liters, user_cards):
    best_discount = 0
    selected_card = None

    for card in user_cards or []:
        if not card_can_affect_recommendation(card):
            continue
        if not brand_matches(get_card_value(card, "brand_scope", "all"), station.brand):
            continue

        min_payment_amount = get_card_value(card, "min_payment_amount", None)
        if min_payment_amount is not None and int(min_payment_amount) > refuel_cost:
            continue

        discount_type = get_card_value(card, "discount_type")
        discount_value = float(get_card_value(card, "discount_value", 0))
        if discount_type == CardPolicy.DiscountType.PER_LITER:
            raw_discount = discount_value * float(target_liters)
        elif discount_type == CardPolicy.DiscountType.PERCENTAGE:
            raw_discount = refuel_cost * discount_value / 100
        elif discount_type == CardPolicy.DiscountType.FIXED_AMOUNT:
            raw_discount = discount_value
        else:
            raw_discount = 0

        discount = round(raw_discount)
        max_discount_amount = get_card_value(card, "max_discount_amount", None)
        monthly_remaining_discount = get_card_value(card, "monthly_remaining_discount", None)
        if max_discount_amount is not None:
            discount = min(discount, int(max_discount_amount))
        if monthly_remaining_discount is not None:
            discount = min(discount, int(monthly_remaining_discount))
        discount = max(discount, 0)

        if discount > best_discount:
            best_discount = discount
            selected_card = serialize_selected_card(card, discount)

    return best_discount, selected_card


def build_recommendation_reason(
    recommendation,
    baseline_cost,
    cheapest_candidate,
    closest_candidate,
    is_winner=False,
):
    station = recommendation.candidate.station
    fuel_price = recommendation.candidate.fuel_price_per_liter
    cost = recommendation.effective_total_cost
    saving = baseline_cost - cost
    prefix = "추천 주유소입니다." if is_winner else "후보 주유소입니다."
    comparison_parts = []

    if cheapest_candidate and cheapest_candidate.station.id != station.id:
        comparison_parts.append(
            f"리터당 최저가 주유소({cheapest_candidate.station.name})보다 "
            f"카드 할인과 이동 비용을 반영한 최종 비용이 유리합니다"
        )
    if closest_candidate and closest_candidate.station.id != station.id:
        comparison_parts.append(
            f"가장 가까운 주유소({closest_candidate.station.name})와 비교해도 "
            f"최종 예상 비용 기준으로 경쟁력이 있습니다"
        )
    if not comparison_parts:
        comparison_parts.append("가격, 거리, 할인 조건을 같은 기준으로 비교했습니다")

    if recommendation.selected_card:
        card = recommendation.selected_card
        return (
            f"{prefix} {station.name}은 {recommendation.target_liters:.2f}L 기준 "
            f"리터당 {fuel_price} KRW, 기본 주유비 {recommendation.refuel_cost} KRW입니다. "
            f"{card['issuer_name']} {card['card_name']} 카드가 "
            f"{recommendation.card_discount_amount} KRW 할인(할인 유형: {card['discount_type']}, "
            f"할인값: {card['discount_value']})을 적용했고, "
            f"왕복 이동 비용은 {recommendation.travel_cost} KRW입니다. "
            f"최종 예상 비용은 {cost} KRW이며 기준 비용 대비 절감액은 {saving} KRW입니다. "
            f"{' '.join(comparison_parts)}."
        )

    return (
        f"{prefix} {station.name}은 {recommendation.target_liters:.2f}L 기준 "
        f"리터당 {fuel_price} KRW, 기본 주유비 {recommendation.refuel_cost} KRW입니다. "
        f"적용 가능한 카드 할인은 없고, 왕복 이동 비용은 {recommendation.travel_cost} KRW입니다. "
        f"최종 예상 비용은 {cost} KRW이며 기준 비용 대비 절감액은 {saving} KRW입니다. "
        f"{' '.join(comparison_parts)}."
    )


def quote_travel_cost_recommendations(
    location,
    radius_km,
    fuel_type,
    target_liters,
    fuel_efficiency_kmpl,
    travel_mode,
    user_cards=None,
):
    candidates = get_station_candidates(location=location, radius_km=radius_km, fuel_type=fuel_type)
    if not candidates:
        return []

    baseline_cost = min(
        calculate_refuel_cost(candidate.fuel_price_per_liter, target_liters)
        + calculate_travel_cost(
            candidate.distance_km,
            fuel_efficiency_kmpl,
            candidate.fuel_price_per_liter,
            travel_mode,
        )
        for candidate in candidates
    )

    draft_recommendations = []
    for candidate in candidates:
        refuel_cost = calculate_refuel_cost(candidate.fuel_price_per_liter, target_liters)
        travel_cost = calculate_travel_cost(
            candidate.distance_km,
            fuel_efficiency_kmpl,
            candidate.fuel_price_per_liter,
            travel_mode,
        )
        card_discount_amount, selected_card = calculate_card_discount(
            candidate.station,
            refuel_cost,
            target_liters,
            user_cards,
        )
        effective_total_cost = refuel_cost - card_discount_amount + travel_cost
        draft_recommendations.append(
            FuelPriceRecommendation(
                candidate=candidate,
                target_liters=round(float(target_liters), 2),
                refuel_cost=refuel_cost,
                card_discount_amount=card_discount_amount,
                travel_cost=travel_cost,
                effective_total_cost=effective_total_cost,
                estimated_saving=baseline_cost - effective_total_cost,
                selected_card=selected_card,
                reason="",
            )
        )

    sorted_drafts = sorted(
        draft_recommendations,
        key=lambda item: (
            item.effective_total_cost,
            item.candidate.distance_km,
            item.candidate.fuel_price_per_liter,
            item.candidate.station.id,
        ),
    )
    cheapest_candidate = min(candidates, key=lambda item: (item.fuel_price_per_liter, item.distance_km, item.station.id))
    closest_candidate = min(candidates, key=lambda item: (item.distance_km, item.fuel_price_per_liter, item.station.id))

    recommendations = []
    for index, item in enumerate(sorted_drafts):
        recommendations.append(
            FuelPriceRecommendation(
                candidate=item.candidate,
                target_liters=item.target_liters,
                refuel_cost=item.refuel_cost,
                card_discount_amount=item.card_discount_amount,
                travel_cost=item.travel_cost,
                effective_total_cost=item.effective_total_cost,
                estimated_saving=item.estimated_saving,
                selected_card=item.selected_card,
                reason=build_recommendation_reason(
                    item,
                    baseline_cost=baseline_cost,
                    cheapest_candidate=cheapest_candidate,
                    closest_candidate=closest_candidate,
                    is_winner=index == 0,
                ),
            )
        )

    return recommendations


def quote_baseline_without_card(recommendations):
    baseline = min(
        recommendations,
        key=lambda item: (
            item.refuel_cost + item.travel_cost,
            item.candidate.distance_km,
            item.candidate.fuel_price_per_liter,
            item.candidate.station.id,
        ),
    )
    return {
        "station_id": baseline.candidate.station.id,
        "effective_cost_without_card": baseline.refuel_cost + baseline.travel_cost,
    }


def quote_fuel_price_only_recommendations(location, radius_km, fuel_type, target_liters):
    return quote_travel_cost_recommendations(
        location=location,
        radius_km=radius_km,
        fuel_type=fuel_type,
        target_liters=target_liters,
        fuel_efficiency_kmpl=1_000_000,
        travel_mode="one_way",
    )
