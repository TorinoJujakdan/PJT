from unittest.mock import patch

from django.test import SimpleTestCase
from fastapi.testclient import TestClient
from search_api.main import app


class SearchAPITest(SimpleTestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/search-api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "search-api"})

    @patch("search_api.main.geocode_query_with_meta")
    def test_location_search_delegates_to_shared_geocode_service(self, mock_geocode):
        mock_geocode.return_value = {
            "results": [
                {
                    "name": "멀티캠퍼스",
                    "address": "서울특별시 강남구 테헤란로 212",
                    "road_address": "서울특별시 강남구 테헤란로 212",
                    "jibun_address": "",
                    "latitude": 37.5012743,
                    "longitude": 127.039585,
                    "source": "naver_local_search",
                }
            ],
            "meta": {"source": "naver_local_search", "status": "ok", "count": 1},
        }

        response = self.client.get(
            "/search-api/locations/search/",
            params={"query": "멀티캠퍼스"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meta"]["source"], "naver_local_search")
        self.assertEqual(response.json()["results"][0]["name"], "멀티캠퍼스")
        mock_geocode.assert_called_once_with("멀티캠퍼스")

    def test_location_search_requires_non_empty_query(self):
        response = self.client.get("/search-api/locations/search/", params={"query": ""})

        self.assertEqual(response.status_code, 422)
