from importlib import import_module
from unittest.mock import patch

from django.test import SimpleTestCase


GEOCODE_RESULT = {
    "name": "Seoul Gangnam-gu Teheran-ro 152",
    "address": "Seoul Gangnam-gu Teheran-ro 152",
    "road_address": "Seoul Gangnam-gu Teheran-ro 152",
    "jibun_address": "",
    "latitude": 37.5007,
    "longitude": 127.0365,
    "source": "naver_geocode",
}
LOCAL_RESULT = {
    "name": "COEX",
    "address": "Seoul Gangnam-gu Yeongdong-daero 513",
    "road_address": "Seoul Gangnam-gu Yeongdong-daero 513",
    "jibun_address": "Seoul Gangnam-gu Samseong-dong 159",
    "latitude": 37.5112994,
    "longitude": 127.059159,
    "source": "naver_local_search",
    "category": "Culture, Art > Exhibition",
}


def geocode_ok(results):
    return {
        "results": results,
        "meta": {
            "source": "naver_geocode",
            "status": "ok",
            "count": len(results),
        },
    }


def unavailable(source, reason):
    return {
        "results": [],
        "meta": {
            "source": source,
            "status": "unavailable",
            "reason": reason,
        },
    }


class LocationSearchRouterTests(SimpleTestCase):
    def setUp(self):
        self.router = import_module("stations.location_search_router")
        self.geocoding = import_module("stations.naver_geocoding_client")
        self.local = import_module("stations.naver_local_search_client")

    def search_with(self, geocode_payload, local_payload=None):
        with (
            patch.object(
                self.geocoding,
                "geocode_query_with_meta",
                return_value=geocode_payload,
            ),
            patch.object(
                self.local,
                "local_search_query_with_meta",
                return_value=local_payload,
            ) as local_search,
        ):
            payload = self.router.geocode_query_with_meta("COEX")

        return payload, local_search

    def test_returns_geocode_results_without_local_fallback(self):
        payload, local_search = self.search_with(geocode_ok([GEOCODE_RESULT]))

        self.assertEqual(payload, geocode_ok([GEOCODE_RESULT]))
        local_search.assert_not_called()

    def test_uses_local_results_after_empty_geocode(self):
        local_payload = {
            "results": [LOCAL_RESULT],
            "meta": {
                "source": "naver_local_search",
                "status": "ok",
                "count": 1,
            },
        }

        payload, _local_search = self.search_with(geocode_ok([]), local_payload)

        self.assertEqual(
            payload["meta"],
            {
                "source": "naver_local_search",
                "status": "ok",
                "count": 1,
                "fallback_from": "naver_geocode",
                "fallback_reason": "GEOCODE_EMPTY",
            },
        )

    def test_preserves_geocode_unavailable_reason(self):
        local_payload = {
            "results": [LOCAL_RESULT],
            "meta": {
                "source": "naver_local_search",
                "status": "ok",
                "count": 1,
            },
        }

        payload, _local_search = self.search_with(
            unavailable("naver_geocode", "NAVER_GEOCODING_KEY_MISSING"),
            local_payload,
        )

        self.assertEqual(
            payload["meta"],
            {
                "source": "naver_local_search",
                "status": "ok",
                "count": 1,
                "fallback_from": "naver_geocode",
                "fallback_reason": "NAVER_GEOCODING_KEY_MISSING",
            },
        )

    def test_reports_both_providers_unavailable(self):
        payload, _local_search = self.search_with(
            unavailable("naver_geocode", "NAVER_GEOCODING_HTTP_401"),
            unavailable("naver_local_search", "NAVER_LOCAL_KEY_MISSING"),
        )

        self.assertEqual(
            payload["meta"],
            {
                "source": "naver_geocode",
                "status": "unavailable",
                "reason": "NAVER_GEOCODING_HTTP_401",
                "fallback_source": "naver_local_search",
                "fallback_status": "unavailable",
                "fallback_reason": "NAVER_LOCAL_KEY_MISSING",
            },
        )

    def test_reports_empty_geocode_and_unavailable_local(self):
        payload, _local_search = self.search_with(
            geocode_ok([]),
            unavailable("naver_local_search", "NAVER_LOCAL_HTTP_401"),
        )

        self.assertEqual(
            payload["meta"],
            {
                "source": "naver_geocode",
                "status": "ok",
                "count": 0,
                "fallback_source": "naver_local_search",
                "fallback_status": "unavailable",
                "fallback_reason": "NAVER_LOCAL_HTTP_401",
            },
        )

    def test_reports_both_providers_successfully_empty(self):
        local_payload = {
            "results": [],
            "meta": {
                "source": "naver_local_search",
                "status": "ok",
                "count": 0,
            },
        }

        payload, _local_search = self.search_with(geocode_ok([]), local_payload)

        self.assertEqual(
            payload["meta"],
            {
                "source": "naver_geocode",
                "status": "ok",
                "count": 0,
                "fallback_source": "naver_local_search",
                "fallback_status": "ok",
                "fallback_count": 0,
            },
        )

    def test_reports_unavailable_geocode_and_successfully_empty_local(self):
        local_payload = {
            "results": [],
            "meta": {
                "source": "naver_local_search",
                "status": "ok",
                "count": 0,
            },
        }

        payload, _local_search = self.search_with(
            unavailable("naver_geocode", "NAVER_GEOCODING_HTTP_401"),
            local_payload,
        )

        self.assertEqual(
            payload,
            {
                "results": [],
                "meta": {
                    "source": "naver_geocode",
                    "status": "unavailable",
                    "reason": "NAVER_GEOCODING_HTTP_401",
                    "fallback_source": "naver_local_search",
                    "fallback_status": "ok",
                    "fallback_count": 0,
                },
            },
        )

    def test_metadata_never_contains_route_decision_or_null_optionals(self):
        payload, _local_search = self.search_with(
            geocode_ok([]),
            unavailable("naver_local_search", "NAVER_LOCAL_KEY_MISSING"),
        )

        self.assertNotIn("route_decision", payload["meta"])
        self.assertNotIn(None, payload["meta"].values())
