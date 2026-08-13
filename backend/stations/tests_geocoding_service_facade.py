from unittest.mock import patch

from django.test import TestCase
from fastapi.testclient import TestClient
from rest_framework.test import APIClient
from search_api.main import app

from stations import geocoding_service

EXPECTED_EXPORTS = [
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


class GeocodingServiceFacadeTests(TestCase):
    def setUp(self):
        self.django_client = APIClient()
        self.fastapi_client = TestClient(app)

    def test_exports_exact_compatibility_surface(self):
        self.assertEqual(geocoding_service.__all__, EXPECTED_EXPORTS)
        for private_name in (
            "_request_naver_json",
            "_request_naver_local_json",
            "_normalize_route_path",
        ):
            with self.subTest(private_name=private_name):
                self.assertFalse(hasattr(geocoding_service, private_name))

    def test_django_empty_query_returns_custom_400(self):
        response = self.django_client.get(
            "/api/v1/stations/geocode/",
            {"query": ""},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "MISSING_QUERY")
        self.assertEqual(
            response.json()["message"],
            "검색어(query) 파라미터가 누락되었습니다.",
        )

    def test_fastapi_empty_query_returns_validation_422(self):
        response = self.fastapi_client.get(
            "/search-api/locations/search/",
            params={"query": ""},
        )

        self.assertEqual(response.status_code, 422)

    def test_django_and_fastapi_return_same_search_contract(self):
        payload = {
            "results": [LOCAL_RESULT],
            "meta": {
                "source": "naver_local_search",
                "status": "ok",
                "count": 1,
                "fallback_from": "naver_geocode",
                "fallback_reason": "GEOCODE_EMPTY",
            },
        }

        with (
            patch(
                "stations.geocoding_service.geocode_query_with_meta",
                return_value=payload,
            ),
            patch(
                "search_api.main.geocode_query_with_meta",
                return_value=payload,
            ),
        ):
            django_response = self.django_client.get(
                "/api/v1/stations/geocode/",
                {"query": "COEX"},
            )
            fastapi_response = self.fastapi_client.get(
                "/search-api/locations/search/",
                params={"query": "COEX"},
            )

        self.assertEqual(django_response.json(), fastapi_response.json())


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
