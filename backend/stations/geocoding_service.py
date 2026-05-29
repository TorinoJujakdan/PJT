import json
import logging
import os
import re
from urllib.error import HTTPError
import urllib.parse
import urllib.request


logger = logging.getLogger(__name__)

GEOCODING_URL = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
REVERSE_GEOCODING_URL = "https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc"
DIRECTIONS_URL = "https://maps.apigw.ntruss.com/map-direction/v1/driving"
LOCAL_SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"
REQUEST_TIMEOUT_SECONDS = 5


def _naver_credentials():
    client_id = (
        os.getenv("NAVER_GEOCODING_CLIENT_ID", "").strip()
        or os.getenv("NAVER_CLIENT_ID", "").strip()
    )
    client_secret = (
        os.getenv("NAVER_GEOCODING_CLIENT_SECRET", "").strip()
        or os.getenv("NAVER_CLIENT_SECRET", "").strip()
    )
    return client_id, client_secret


def _naver_local_credentials():
    client_id = (
        os.getenv("NAVER_LOCAL_CLIENT_ID", "").strip()
        or os.getenv("NAVER_SEARCH_CLIENT_ID", "").strip()
        or os.getenv("NAVER_OPENAPI_CLIENT_ID", "").strip()
        or os.getenv("NAVER_CLIENT_ID", "").strip()
    )
    client_secret = (
        os.getenv("NAVER_LOCAL_CLIENT_SECRET", "").strip()
        or os.getenv("NAVER_SEARCH_CLIENT_SECRET", "").strip()
        or os.getenv("NAVER_OPENAPI_CLIENT_SECRET", "").strip()
        or os.getenv("NAVER_CLIENT_SECRET", "").strip()
    )
    return client_id, client_secret


def _request_naver_json(url):
    client_id, client_secret = _naver_credentials()
    if not client_id or not client_secret:
        return None, "NAVER_GEOCODING_KEY_MISSING"

    request = urllib.request.Request(url)
    request.add_header("x-ncp-apigw-api-key-id", client_id)
    request.add_header("x-ncp-apigw-api-key", client_secret)
    request.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                return None, f"NAVER_GEOCODING_HTTP_{response.status}"
            return json.loads(response.read().decode("utf-8")), None
    except HTTPError as exc:
        return None, f"NAVER_GEOCODING_HTTP_{exc.code}"
    except Exception as exc:
        logger.warning("Naver geocoding request failed: %s", exc, exc_info=True)
        return None, "NAVER_GEOCODING_REQUEST_FAILED"


def _request_naver_local_json(url):
    client_id, client_secret = _naver_local_credentials()
    if not client_id or not client_secret:
        return None, "NAVER_LOCAL_KEY_MISSING"

    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                return None, f"NAVER_LOCAL_HTTP_{response.status}"
            return json.loads(response.read().decode("utf-8")), None
    except HTTPError as exc:
        return None, f"NAVER_LOCAL_HTTP_{exc.code}"
    except Exception as exc:
        logger.warning("Naver local search request failed: %s", exc, exc_info=True)
        return None, "NAVER_LOCAL_REQUEST_FAILED"


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_html(value):
    return re.sub(r"<[^>]+>", "", value or "").strip()


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


def geocode_query_with_meta(query):
    query = (query or "").strip()
    if not query:
        return {
            "results": [],
            "meta": {
                "source": "naver_geocode",
                "status": "empty_query",
            },
        }

    url = f"{GEOCODING_URL}?query={urllib.parse.quote(query)}"
    payload, reason = _request_naver_json(url)
    if payload is None:
        local_payload = local_search_query_with_meta(query)
        if local_payload["results"]:
            local_payload["meta"]["fallback_from"] = "naver_geocode"
            local_payload["meta"]["fallback_reason"] = reason
            return local_payload
        return {
            "results": [],
            "meta": {
                "source": "naver_geocode",
                "status": "unavailable",
                "reason": reason,
                "fallback_source": local_payload["meta"].get("source"),
                "fallback_status": local_payload["meta"].get("status"),
                "fallback_reason": local_payload["meta"].get("reason"),
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
    if not results:
        local_payload = local_search_query_with_meta(query)
        if local_payload["results"]:
            return local_payload
        return {
            "results": [],
            "meta": {
                "source": "naver_geocode",
                "status": "ok",
                "count": 0,
                "fallback_source": local_payload["meta"].get("source"),
                "fallback_status": local_payload["meta"].get("status"),
                "fallback_reason": local_payload["meta"].get("reason"),
            },
        }

    return {
        "results": results,
        "meta": {
            "source": "naver_geocode",
            "status": "ok",
            "count": len(results),
        },
    }


def geocode_query(query):
    return geocode_query_with_meta(query)["results"]


def _normalize_local_search_item(item, fallback_name):
    latitude = _safe_float(item.get("mapy"))
    longitude = _safe_float(item.get("mapx"))
    if latitude is None or longitude is None:
        return None

    # Naver Local Search returns longitude/latitude scaled by 10,000,000.
    if abs(latitude) > 90 or abs(longitude) > 180:
        latitude = latitude / 10000000
        longitude = longitude / 10000000

    if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
        return None

    road_address = item.get("roadAddress") or ""
    jibun_address = item.get("address") or ""
    display_address = road_address or jibun_address
    return {
        "name": _clean_html(item.get("title")) or display_address or fallback_name,
        "address": display_address,
        "road_address": road_address,
        "jibun_address": jibun_address,
        "latitude": latitude,
        "longitude": longitude,
        "source": "naver_local_search",
        "category": item.get("category") or "",
    }


def local_search_query_with_meta(query):
    params = urllib.parse.urlencode({"query": query, "display": 5, "sort": "random"})
    payload, reason = _request_naver_local_json(f"{LOCAL_SEARCH_URL}?{params}")
    if payload is None:
        return {
            "results": [],
            "meta": {
                "source": "naver_local_search",
                "status": "unavailable",
                "reason": reason,
            },
        }

    results = [
        normalized
        for normalized in (
            _normalize_local_search_item(item, query)
            for item in payload.get("items", [])
        )
        if normalized is not None
    ]
    return {
        "results": results,
        "meta": {
            "source": "naver_local_search",
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
        road_tail = " ".join(item for item in [road_name, land_number] if item)
        return " ".join([*region_parts, road_tail]).strip()

    return " ".join([*region_parts, land_number]).strip()


def reverse_geocode_with_meta(latitude, longitude):
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
    payload, reason = _request_naver_json(f"{REVERSE_GEOCODING_URL}?{params}")
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


def reverse_geocode(latitude, longitude):
    return reverse_geocode_with_meta(latitude, longitude)["result"]


def _normalize_route_path(raw_path):
    normalized = []
    for point in raw_path or []:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        longitude = _safe_float(point[0])
        latitude = _safe_float(point[1])
        if latitude is None or longitude is None:
            continue
        normalized.append({"latitude": latitude, "longitude": longitude})
    return normalized


def get_driving_route_with_path(start_lat, start_lng, goal_lat, goal_lng):
    """
    Naver Directions 5 API? ???? ?? ?? ?? ??(m), ?? ??(ms), ?? ??? ????.
    (distance_meters, duration_ms, route_path, error_code) ??? ?????.
    """
    client_id, client_secret = _naver_credentials()
    if not client_id or not client_secret:
        return None, None, [], "NAVER_KEYS_MISSING"

    params = urllib.parse.urlencode({
        "start": f"{start_lng},{start_lat}",
        "goal": f"{goal_lng},{goal_lat}",
        "option": "traoptimal"
    })

    url = f"{DIRECTIONS_URL}?{params}"

    request = urllib.request.Request(url)
    request.add_header("x-ncp-apigw-api-key-id", client_id)
    request.add_header("x-ncp-apigw-api-key", client_secret)
    request.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                return None, None, [], f"NAVER_DIRECTIONS_HTTP_{response.status}"
            data = json.loads(response.read().decode("utf-8"))

            if "route" in data and "traoptimal" in data["route"] and len(data["route"]["traoptimal"]) > 0:
                route = data["route"]["traoptimal"][0]
                summary = route.get("summary", {})
                distance = summary.get("distance")  # meters
                duration = summary.get("duration")  # milliseconds
                route_path = _normalize_route_path(route.get("path", []))
                return distance, duration, route_path, None
            return None, None, [], "INVALID_RESPONSE_FORMAT"
    except HTTPError as exc:
        return None, None, [], f"NAVER_DIRECTIONS_HTTP_{exc.code}"
    except Exception as exc:
        logger.warning("Naver directions API request failed: %s", exc, exc_info=True)
        return None, None, [], "REQUEST_FAILED"


def get_driving_route(start_lat, start_lng, goal_lat, goal_lng):
    distance, duration, _route_path, error = get_driving_route_with_path(
        start_lat,
        start_lng,
        goal_lat,
        goal_lng,
    )
    return distance, duration, error
