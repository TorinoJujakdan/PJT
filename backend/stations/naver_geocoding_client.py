import json
import logging
from urllib.error import HTTPError, URLError
import urllib.parse
import urllib.request

from .naver_maps_auth import get_naver_maps_credentials


logger = logging.getLogger(__name__)

GEOCODING_URL = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
REVERSE_GEOCODING_URL = "https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc"
REQUEST_TIMEOUT_SECONDS = 5


def _request_naver_json(url):
    client_id, client_secret = get_naver_maps_credentials()
    if not client_id or not client_secret:
        return None, "NAVER_GEOCODING_KEY_MISSING"

    request = urllib.request.Request(url)
    request.add_header("x-ncp-apigw-api-key-id", client_id)
    request.add_header("x-ncp-apigw-api-key", client_secret)
    request.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            if response.status != 200:
                return None, f"NAVER_GEOCODING_HTTP_{response.status}"
            return json.loads(response.read().decode("utf-8")), None
    except HTTPError as exc:
        return None, f"NAVER_GEOCODING_HTTP_{exc.code}"
    except (URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Naver geocoding request failed: %s", exc, exc_info=True)
        return None, "NAVER_GEOCODING_REQUEST_FAILED"


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_geocode_address(address, fallback_name):
    latitude = _safe_float(address.get("y"))
    longitude = _safe_float(address.get("x"))
    if latitude is None or longitude is None:
        return None

    road_address = address.get("roadAddress") or ""
    jibun_address = address.get("jibunAddress") or ""
    display_address = road_address or jibun_address
    return {
        "name": display_address or fallback_name,
        "address": display_address,
        "road_address": road_address,
        "jibun_address": jibun_address,
        "latitude": latitude,
        "longitude": longitude,
        "source": "naver_geocode",
    }


def geocode_query_with_meta(query, request_json=None):
    query = (query or "").strip()
    if not query:
        return {
            "results": [],
            "meta": {
                "source": "naver_geocode",
                "status": "empty_query",
            },
        }

    requester = request_json or _request_naver_json
    url = f"{GEOCODING_URL}?query={urllib.parse.quote(query)}"
    payload, reason = requester(url)
    if payload is None:
        return {
            "results": [],
            "meta": {
                "source": "naver_geocode",
                "status": "unavailable",
                "reason": reason,
            },
        }

    results = [
        normalized
        for normalized in (
            _normalize_geocode_address(item, query)
            for item in payload.get("addresses", [])
        )
        if normalized is not None
    ]
    return {
        "results": results,
        "meta": {
            "source": "naver_geocode",
            "status": "ok",
            "count": len(results),
        },
    }


def _region_parts(region):
    if not region:
        return []
    parts = []
    for key in ["area1", "area2", "area3", "area4"]:
        name = region.get(key, {}).get("name")
        if name:
            parts.append(name)
    return parts


def _land_number(land):
    number1 = land.get("number1")
    number2 = land.get("number2")
    if number1 and number2:
        return f"{number1}-{number2}"
    return number1 or ""


def _format_reverse_address(result):
    region_parts = _region_parts(result.get("region"))
    land = result.get("land") or {}
    land_number = _land_number(land)

    if result.get("name") == "roadaddr":
        road_name = land.get("name")
        road_tail = " ".join(
            item for item in [road_name, land_number] if item
        )
        return " ".join([*region_parts, road_tail]).strip()

    return " ".join([*region_parts, land_number]).strip()


def reverse_geocode_with_meta(latitude, longitude, request_json=None):
    lat = _safe_float(latitude)
    lon = _safe_float(longitude)
    if lat is None or lon is None:
        return {
            "result": None,
            "meta": {
                "source": "naver_reverse_geocode",
                "status": "invalid_location",
            },
        }

    params = urllib.parse.urlencode(
        {
            "coords": f"{lon},{lat}",
            "orders": "roadaddr,addr",
            "output": "json",
        }
    )
    requester = request_json or _request_naver_json
    payload, reason = requester(f"{REVERSE_GEOCODING_URL}?{params}")
    if payload is None:
        return {
            "result": None,
            "meta": {
                "source": "naver_reverse_geocode",
                "status": "unavailable",
                "reason": reason,
            },
        }

    road_address = ""
    jibun_address = ""
    for item in payload.get("results", []):
        formatted = _format_reverse_address(item)
        if item.get("name") == "roadaddr" and formatted:
            road_address = formatted
        elif item.get("name") == "addr" and formatted:
            jibun_address = formatted

    address = road_address or jibun_address
    result = {
        "name": address or f"{lat:.6f}, {lon:.6f}",
        "address": address,
        "road_address": road_address,
        "jibun_address": jibun_address,
        "latitude": lat,
        "longitude": lon,
        "source": "naver_reverse_geocode",
    }
    return {
        "result": result,
        "meta": {
            "source": "naver_reverse_geocode",
            "status": "ok",
            "has_address": bool(address),
        },
    }


def reverse_geocode(latitude, longitude, request_json=None):
    return reverse_geocode_with_meta(
        latitude,
        longitude,
        request_json=request_json,
    )["result"]
