from decimal import Decimal
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import Mock, patch

from cards.models import CardCatalog, CardPolicy
from cards.selenium_ingestion import ScrapedCardCandidate, save_candidates
from stations import geocoding_service
from stations.models import FuelPrice, GasStation


class GeocodeProxyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_geocode_uses_current_naver_cloud_maps_gateway(self):
        self.assertEqual(
            geocoding_service.GEOCODING_URL,
            "https://maps.apigw.ntruss.com/map-geocode/v2/geocode",
        )
        self.assertEqual(
            geocoding_service.REVERSE_GEOCODING_URL,
            "https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc",
        )
        self.assertEqual(
            geocoding_service.DIRECTIONS_URL,
            "https://maps.apigw.ntruss.com/map-direction/v1/driving",
        )

    def test_directions_path_is_normalized_to_latitude_longitude_points(self):
        self.assertEqual(
            geocoding_service._normalize_route_path(
                [
                    [127.039, 37.501],
                    [127.041, 37.503],
                    ["invalid"],
                ]
            ),
            [
                {"latitude": 37.501, "longitude": 127.039},
                {"latitude": 37.503, "longitude": 127.041},
            ],
        )

    def test_geocode_endpoint_returns_naver_results(self):
        payload = {
            "addresses": [
                {
                    "roadAddress": "서울특별시 중구 세종대로 110",
                    "jibunAddress": "서울특별시 중구 태평로1가 31",
                    "x": "126.9780",
                    "y": "37.5665",
                }
            ]
        }
        with patch("stations.geocoding_service._request_naver_json", return_value=(payload, None)):
            response = self.client.get(
                "/api/v1/stations/geocode/",
                {"query": "서울시청"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertEqual(data["meta"]["source"], "naver_geocode")
        results = data["results"]
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["name"], "서울특별시 중구 세종대로 110")
        self.assertAlmostEqual(results[0]["latitude"], 37.5665, places=4)
        self.assertAlmostEqual(results[0]["longitude"], 126.9780, places=4)

    def test_geocode_endpoint_without_keys_returns_empty_results(self):
        with patch.dict("os.environ", {}, clear=True):
            response = self.client.get(
                "/api/v1/stations/geocode/",
                {"query": "서울시청"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["results"], [])
        self.assertEqual(data["meta"]["status"], "unavailable")

    def test_geocode_endpoint_falls_back_to_local_search_for_poi(self):
        local_payload = {
            "items": [
                {
                    "title": "<b>코엑스</b>",
                    "roadAddress": "서울특별시 강남구 영동대로 513",
                    "address": "서울특별시 강남구 삼성동 159",
                    "mapx": "1270591590",
                    "mapy": "375112994",
                    "category": "문화,예술>전시장",
                }
            ]
        }

        with (
            patch("stations.geocoding_service._request_naver_json", return_value=({"addresses": []}, None)),
            patch("stations.geocoding_service._request_naver_local_json", return_value=(local_payload, None)),
        ):
            response = self.client.get(
                "/api/v1/stations/geocode/",
                {"query": "코엑스"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["meta"]["source"], "naver_local_search")
        self.assertEqual(data["results"][0]["name"], "코엑스")
        self.assertAlmostEqual(data["results"][0]["latitude"], 37.5112994, places=6)
        self.assertAlmostEqual(data["results"][0]["longitude"], 127.059159, places=6)

    def test_geocode_endpoint_uses_local_search_when_geocode_unavailable(self):
        local_payload = {
            "items": [
                {
                    "title": "<b>COEX</b>",
                    "roadAddress": "Seoul Gangnam-gu Yeongdong-daero 513",
                    "address": "Seoul Gangnam-gu Samseong-dong 159",
                    "mapx": "1270591590",
                    "mapy": "375112994",
                    "category": "place",
                }
            ]
        }

        with (
            patch("stations.geocoding_service._request_naver_json", return_value=(None, "NAVER_GEOCODING_HTTP_401")),
            patch("stations.geocoding_service._request_naver_local_json", return_value=(local_payload, None)),
        ):
            response = self.client.get(
                "/api/v1/stations/geocode/",
                {"query": "COEX"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["meta"]["source"], "naver_local_search")
        self.assertEqual(data["meta"]["fallback_from"], "naver_geocode")
        self.assertEqual(data["results"][0]["name"], "COEX")
        self.assertAlmostEqual(data["results"][0]["latitude"], 37.5112994, places=6)
        self.assertAlmostEqual(data["results"][0]["longitude"], 127.059159, places=6)

    def test_geocode_endpoint_reports_empty_geocode_fallback_status(self):
        with (
            patch("stations.geocoding_service._request_naver_json", return_value=({"addresses": []}, None)),
            patch(
                "stations.geocoding_service._request_naver_local_json",
                return_value=(None, "NAVER_LOCAL_HTTP_401"),
            ),
        ):
            response = self.client.get(
                "/api/v1/stations/geocode/",
                {"query": "COEX"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["results"], [])
        self.assertEqual(data["meta"]["source"], "naver_geocode")
        self.assertEqual(data["meta"]["status"], "ok")
        self.assertEqual(data["meta"]["count"], 0)
        self.assertEqual(data["meta"]["fallback_source"], "naver_local_search")
        self.assertEqual(data["meta"]["fallback_status"], "unavailable")
        self.assertEqual(data["meta"]["fallback_reason"], "NAVER_LOCAL_HTTP_401")

    def test_geocode_endpoint_missing_query_returns_400(self):
        response = self.client.get(
            "/api/v1/stations/geocode/",
            {"query": ""},
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["code"], "MISSING_QUERY")
        self.assertIn("message", data)

    def test_reverse_geocode_endpoint_returns_address_label(self):
        payload = {
            "results": [
                {
                    "name": "roadaddr",
                    "region": {
                        "area1": {"name": "서울특별시"},
                        "area2": {"name": "중구"},
                        "area3": {"name": "태평로1가"},
                        "area4": {"name": ""},
                    },
                    "land": {"name": "세종대로", "number1": "110", "number2": ""},
                }
            ]
        }
        with patch("stations.geocoding_service._request_naver_json", return_value=(payload, None)):
            response = self.client.get(
                "/api/v1/stations/reverse-geocode/",
                {"latitude": 37.5665, "longitude": 126.978},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["result"]["address"], "서울특별시 중구 태평로1가 세종대로 110")
        self.assertEqual(data["meta"]["source"], "naver_reverse_geocode")


class StationRefreshAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_refresh_skips_gracefully_without_opinet_key(self):
        with patch.dict("os.environ", {}, clear=True):
            response = self.client.post(
                "/api/v1/stations/refresh/",
                {
                    "location": {"latitude": 37.5665, "longitude": 126.978},
                    "fuel_type": "gasoline",
                    "radius_km": 5,
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "skipped")

    def test_refresh_saves_opinet_rows_for_selected_location(self):
        rows = [
            {
                "UNI_ID": "A0010207",
                "POLL_DIV_CD": "SKE",
                "OS_NM": "SK Sample",
                "NEW_ADR": "서울 강남구 역삼로 142",
                "GIS_X_COOR": "314871.80000",
                "GIS_Y_COOR": "544012.00000",
                "PRODCD": "B027",
                "PRICE": "1700",
            }
        ]

        with patch.dict("os.environ", {"OPINET_API_KEY": "test-key"}, clear=True), patch(
            "stations.opinet_client.OpinetClient.fetch_price_rows",
            Mock(return_value=rows),
        ):
            response = self.client.post(
                "/api/v1/stations/refresh/",
                {
                    "location": {"latitude": 37.5665, "longitude": 126.978},
                    "fuel_type": "gasoline",
                    "radius_km": 5,
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        station = GasStation.objects.get(external_station_id="A0010207")
        price = FuelPrice.objects.get(station=station, fuel_type=FuelPrice.FuelType.GASOLINE)
        self.assertEqual(price.price_per_liter, 1700)


class CardAutoVerificationTests(TestCase):
    def test_save_candidates_auto_verifies_high_confidence_card(self):
        # 1. Candidate with high confidence (>= 0.85), valid discount_value (> 0) and non-empty name/issuer
        high_conf_candidate = ScrapedCardCandidate(
            card_name="KB국민 Easy All 카드",
            issuer_name="KB국민카드",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=Decimal("150"),
            confidence=Decimal("0.88"),
            source_url="https://card-search.naver.com/list#candidate-1",
        )

        # 2. Candidate with low confidence (< 0.85)
        low_conf_candidate = ScrapedCardCandidate(
            card_name="신한 Deep Oil 카드",
            issuer_name="신한카드",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
            confidence=Decimal("0.80"),
            source_url="https://card-search.naver.com/list#candidate-2",
        )

        # 3. Candidate with missing issuer name
        missing_issuer_candidate = ScrapedCardCandidate(
            card_name="우리카드 특별할인",
            issuer_name="",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("5000"),
            confidence=Decimal("0.90"),
            source_url="https://card-search.naver.com/list#candidate-3",
        )

        candidates = [high_conf_candidate, low_conf_candidate, missing_issuer_candidate]
        saved_cards = save_candidates(candidates, "https://card-search.naver.com/list")

        self.assertEqual(len(saved_cards), 3)

        # Verify high confidence card is ADMIN_VERIFIED
        card1 = CardCatalog.objects.get(source_url="https://card-search.naver.com/list#candidate-1")
        self.assertEqual(card1.verification_status, CardPolicy.VerificationStatus.ADMIN_VERIFIED)
        self.assertEqual(card1.card_name, "KB국민 Easy All 카드")

        # Verify low confidence card is UNVERIFIED
        card2 = CardCatalog.objects.get(source_url="https://card-search.naver.com/list#candidate-2")
        self.assertEqual(card2.verification_status, CardPolicy.VerificationStatus.UNVERIFIED)

        # Verify missing issuer card is UNVERIFIED
        card3 = CardCatalog.objects.get(source_url="https://card-search.naver.com/list#candidate-3")
        self.assertEqual(card3.verification_status, CardPolicy.VerificationStatus.UNVERIFIED)
