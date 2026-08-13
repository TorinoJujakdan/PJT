from . import naver_geocoding_client, naver_local_search_client


def geocode_query_with_meta(
    query,
    geocode_search=None,
    local_search=None,
):
    geocode = geocode_search or naver_geocoding_client.geocode_query_with_meta
    local = (
        local_search
        or naver_local_search_client.local_search_query_with_meta
    )

    geocode_payload = geocode(query)
    geocode_results = geocode_payload["results"]
    geocode_meta = geocode_payload["meta"]
    if geocode_results or geocode_meta["status"] == "empty_query":
        return geocode_payload

    local_payload = local(query)
    local_results = local_payload["results"]
    local_meta = local_payload["meta"]
    geocode_unavailable = geocode_meta["status"] == "unavailable"

    if local_results:
        fallback_reason = (
            geocode_meta["reason"]
            if geocode_unavailable
            else "GEOCODE_EMPTY"
        )
        return {
            "results": local_results,
            "meta": {
                "source": "naver_local_search",
                "status": "ok",
                "count": len(local_results),
                "fallback_from": "naver_geocode",
                "fallback_reason": fallback_reason,
            },
        }

    if geocode_unavailable:
        fallback_meta = {
            "source": "naver_geocode",
            "status": "unavailable",
            "reason": geocode_meta["reason"],
            "fallback_source": "naver_local_search",
            "fallback_status": local_meta["status"],
        }
        if local_meta["status"] == "unavailable":
            fallback_meta["fallback_reason"] = local_meta["reason"]
        else:
            fallback_meta["fallback_count"] = len(local_results)
        return {
            "results": [],
            "meta": fallback_meta,
        }

    if local_meta["status"] == "unavailable":
        return {
            "results": [],
            "meta": {
                "source": "naver_geocode",
                "status": "ok",
                "count": 0,
                "fallback_source": "naver_local_search",
                "fallback_status": "unavailable",
                "fallback_reason": local_meta["reason"],
            },
        }

    return {
        "results": [],
        "meta": {
            "source": "naver_geocode",
            "status": "ok",
            "count": 0,
            "fallback_source": "naver_local_search",
            "fallback_status": "ok",
            "fallback_count": 0,
        },
    }


def geocode_query(query, geocode_search=None, local_search=None):
    return geocode_query_with_meta(
        query,
        geocode_search=geocode_search,
        local_search=local_search,
    )["results"]
