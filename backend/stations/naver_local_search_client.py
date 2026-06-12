import json
import logging
import os
import re
from urllib.error import HTTPError, URLError
import urllib.parse
import urllib.request


logger = logging.getLogger(__name__)

LOCAL_SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"
REQUEST_TIMEOUT_SECONDS = 5


def get_naver_local_credentials():
    for client_id_key, client_secret_key in (
        ("NAVER_LOCAL_CLIENT_ID", "NAVER_LOCAL_CLIENT_SECRET"),
        ("NAVER_SEARCH_CLIENT_ID", "NAVER_SEARCH_CLIENT_SECRET"),
        ("NAVER_OPENAPI_CLIENT_ID", "NAVER_OPENAPI_CLIENT_SECRET"),
    ):
        client_id = os.getenv(client_id_key, "").strip()
        client_secret = os.getenv(client_secret_key, "").strip()
        if client_id and client_secret:
            return client_id, client_secret
    return "", ""


def _request_naver_local_json(url):
    client_id, client_secret = get_naver_local_credentials()
    if not client_id or not client_secret:
        return None, "NAVER_LOCAL_KEY_MISSING"

    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            if response.status != 200:
                return None, f"NAVER_LOCAL_HTTP_{response.status}"
            return json.loads(response.read().decode("utf-8")), None
    except HTTPError as exc:
        return None, f"NAVER_LOCAL_HTTP_{exc.code}"
    except (URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Naver local search request failed: %s", exc, exc_info=True)
        return None, "NAVER_LOCAL_REQUEST_FAILED"


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_html(value):
    return re.sub(r"<[^>]+>", "", value or "").strip()


def _normalize_local_search_item(item, fallback_name):
    latitude = _safe_float(item.get("mapy"))
    longitude = _safe_float(item.get("mapx"))
    if latitude is None or longitude is None:
        return None

    if abs(latitude) > 90 or abs(longitude) > 180:
        latitude /= 10000000
        longitude /= 10000000

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None

    road_address = item.get("roadAddress") or ""
    jibun_address = item.get("address") or ""
    display_address = road_address or jibun_address
    return {
        "name": _clean_html(item.get("title"))
        or display_address
        or fallback_name,
        "address": display_address,
        "road_address": road_address,
        "jibun_address": jibun_address,
        "latitude": latitude,
        "longitude": longitude,
        "source": "naver_local_search",
        "category": item.get("category") or "",
    }


def local_search_query_with_meta(query, request_json=None):
    params = urllib.parse.urlencode(
        {"query": query, "display": 5, "sort": "random"}
    )
    requester = request_json or _request_naver_local_json
    payload, reason = requester(f"{LOCAL_SEARCH_URL}?{params}")
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
