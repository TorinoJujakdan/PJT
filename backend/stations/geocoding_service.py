from . import location_search_router
from . import naver_geocoding_client
from .naver_directions_client import (
    DIRECTIONS_URL,
    get_driving_route,
    get_driving_route_with_path,
)
from .naver_geocoding_client import GEOCODING_URL, REVERSE_GEOCODING_URL


__all__ = [
    "GEOCODING_URL",
    "REVERSE_GEOCODING_URL",
    "DIRECTIONS_URL",
    "geocode_query_with_meta",
    "geocode_query",
    "reverse_geocode_with_meta",
    "reverse_geocode",
    "get_driving_route_with_path",
    "get_driving_route",
]


def geocode_query_with_meta(query):
    return location_search_router.geocode_query_with_meta(query)


def geocode_query(query):
    return geocode_query_with_meta(query)["results"]


def reverse_geocode_with_meta(latitude, longitude):
    return naver_geocoding_client.reverse_geocode_with_meta(
        latitude,
        longitude,
    )


def reverse_geocode(latitude, longitude):
    return reverse_geocode_with_meta(latitude, longitude)["result"]
