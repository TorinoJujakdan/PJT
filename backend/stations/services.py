from dataclasses import dataclass
from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

from django.db.models import OuterRef, Subquery

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
    selected_card: None
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


def quote_travel_cost_recommendations(
    location,
    radius_km,
    fuel_type,
    target_liters,
    fuel_efficiency_kmpl,
    travel_mode,
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

    recommendations = []
    for candidate in candidates:
        refuel_cost = calculate_refuel_cost(candidate.fuel_price_per_liter, target_liters)
        travel_cost = calculate_travel_cost(
            candidate.distance_km,
            fuel_efficiency_kmpl,
            candidate.fuel_price_per_liter,
            travel_mode,
        )
        effective_total_cost = refuel_cost + travel_cost
        recommendations.append(
            FuelPriceRecommendation(
                candidate=candidate,
                target_liters=round(float(target_liters), 2),
                refuel_cost=refuel_cost,
                card_discount_amount=0,
                travel_cost=travel_cost,
                effective_total_cost=effective_total_cost,
                estimated_saving=baseline_cost - effective_total_cost,
                selected_card=None,
                reason="주유비와 차량 연비 기반 이동 비용을 함께 비교했을 때 최종 예상 비용이 가장 낮은 후보입니다.",
            )
        )

    return sorted(
        recommendations,
        key=lambda item: (
            item.effective_total_cost,
            item.candidate.distance_km,
            item.candidate.fuel_price_per_liter,
            item.candidate.station.id,
        ),
    )


def quote_fuel_price_only_recommendations(location, radius_km, fuel_type, target_liters):
    return quote_travel_cost_recommendations(
        location=location,
        radius_km=radius_km,
        fuel_type=fuel_type,
        target_liters=target_liters,
        fuel_efficiency_kmpl=1_000_000,
        travel_mode="one_way",
    )
