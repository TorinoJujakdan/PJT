import json
import logging
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

from .naver_maps_auth import get_naver_maps_credentials

logger = logging.getLogger(__name__)

DIRECTIONS_URL = "https://maps.apigw.ntruss.com/map-direction/v1/driving"
REQUEST_TIMEOUT_SECONDS = 5


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_route_path(raw_path):
    normalized = []
    for point in raw_path or []:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        longitude = _safe_float(point[0])
        latitude = _safe_float(point[1])
        if latitude is None or longitude is None:
            continue
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            continue
        normalized.append(
            {"latitude": latitude, "longitude": longitude}
        )
    return normalized


def get_driving_route_with_path(start_lat, start_lng, goal_lat, goal_lng):
    client_id, client_secret = get_naver_maps_credentials()
    if not client_id or not client_secret:
        return None, None, [], "NAVER_KEYS_MISSING"

    params = urllib.parse.urlencode(
        {
            "start": f"{start_lng},{start_lat}",
            "goal": f"{goal_lng},{goal_lat}",
            "option": "traoptimal",
        }
    )
    request = urllib.request.Request(f"{DIRECTIONS_URL}?{params}")
    request.add_header("x-ncp-apigw-api-key-id", client_id)
    request.add_header("x-ncp-apigw-api-key", client_secret)
    request.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            if response.status != 200:
                return (
                    None,
                    None,
                    [],
                    f"NAVER_DIRECTIONS_HTTP_{response.status}",
                )
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return None, None, [], f"NAVER_DIRECTIONS_HTTP_{exc.code}"
    except (URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning(
            "Naver directions API request failed: %s",
            exc,
            exc_info=True,
        )
        return None, None, [], "REQUEST_FAILED"

    routes = data.get("route", {}).get("traoptimal", [])
    if not routes:
        return None, None, [], "INVALID_RESPONSE_FORMAT"

    route = routes[0]
    summary = route.get("summary", {})
    return (
        summary.get("distance"),
        summary.get("duration"),
        _normalize_route_path(route.get("path", [])),
        None,
    )


def get_driving_route(start_lat, start_lng, goal_lat, goal_lng):
    distance, duration, _route_path, error = get_driving_route_with_path(
        start_lat,
        start_lng,
        goal_lat,
        goal_lng,
    )
    return distance, duration, error
