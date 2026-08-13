import concurrent.futures


def fetch_directions_parallel(start_lat, start_lng, candidates_to_route):
    """
    후보들에 대해 병렬로 Naver Directions API를 호출하여 도로 주행 정보(거리, 시간)를 구합니다.
    """
    from .geocoding_service import get_driving_route_with_path

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_candidate = {
            executor.submit(
                get_driving_route_with_path,
                start_lat,
                start_lng,
                float(cand.station.latitude),
                float(cand.station.longitude)
            ): cand.station.id
            for cand in candidates_to_route
        }
        for future in concurrent.futures.as_completed(future_to_candidate):
            cand_id = future_to_candidate[future]
            try:
                distance_m, duration_ms, route_path, err = future.result()
                if err is None and distance_m is not None:
                    results[cand_id] = {
                        "distance_km": round(distance_m / 1000.0, 2),
                        "duration_min": round(duration_ms / 60000.0, 1),
                        "distance_source": "naver_directions",
                        "route_path": route_path,
                    }
                else:
                    results[cand_id] = {
                        "distance_km": None,
                        "duration_min": None,
                        "distance_source": "haversine",
                        "route_path": [],
                        "error": err
                    }
            except Exception as e:
                results[cand_id] = {
                    "distance_km": None,
                    "duration_min": None,
                    "distance_source": "haversine",
                    "route_path": [],
                    "error": str(e)
                }
    return results
