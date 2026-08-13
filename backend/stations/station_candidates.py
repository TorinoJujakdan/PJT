from dataclasses import dataclass
from decimal import Decimal
from math import asin, cos, radians, sin, sqrt
from typing import Any, Optional

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
    price_collected_at: Optional[Any] = None
    price_source: Optional[str] = None



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

    latest_price_val = (
        FuelPrice.objects.filter(station=OuterRef("pk"), fuel_type=fuel_type)
        .order_by("-collected_at", "-id")
    )

    queryset = (
        GasStation.objects.filter(
            latitude__gte=bbox["min_latitude"],
            latitude__lte=bbox["max_latitude"],
            longitude__gte=bbox["min_longitude"],
            longitude__lte=bbox["max_longitude"],
        )
        .annotate(
            fuel_price_per_liter=Subquery(latest_price_val.values("price_per_liter")[:1]),
            fuel_price_collected_at=Subquery(latest_price_val.values("collected_at")[:1]),
            fuel_price_source=Subquery(latest_price_val.values("source")[:1]),
        )
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
                    price_collected_at=station.fuel_price_collected_at,
                    price_source=station.fuel_price_source,
                )
            )

    return sorted(candidates, key=lambda item: (item.distance_km, item.fuel_price_per_liter, item.station.id))
