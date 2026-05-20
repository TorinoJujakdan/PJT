from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from cards.models import CardPolicy
from stations.models import FuelPrice, GasStation
from vehicles.models import VehicleProfile


class NearbyStationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_dummy_stations", verbosity=0)

    def setUp(self):
        self.client = APIClient()

    def test_nearby_stations_returns_candidates_inside_radius(self):
        response = self.client.get(
            "/api/v1/stations/nearby/",
            {
                "latitude": 37.501,
                "longitude": 127.039,
                "fuel_type": "gasoline",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["meta"]["count"], 4)
        self.assertEqual(data["meta"]["radius_km"], 15)
        self.assertEqual(data["stations"][0]["distance_source"], "haversine")
        self.assertEqual(data["stations"][0]["fuel_type"], "gasoline")
        self.assertIn("fuel_price_per_liter", data["stations"][0])

    def test_invalid_location_returns_contract_error(self):
        response = self.client.get(
            "/api/v1/stations/nearby/",
            {
                "latitude": 91,
                "longitude": 127.039,
                "fuel_type": "gasoline",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_LOCATION")

    def test_invalid_fuel_type_returns_contract_error(self):
        response = self.client.get(
            "/api/v1/stations/nearby/",
            {
                "latitude": 37.501,
                "longitude": 127.039,
                "fuel_type": "hydrogen",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "UNSUPPORTED_FUEL_TYPE")

    def test_invalid_radius_returns_contract_error(self):
        response = self.client.get(
            "/api/v1/stations/nearby/",
            {
                "latitude": 37.501,
                "longitude": 127.039,
                "fuel_type": "gasoline",
                "radius_km": 31,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_RADIUS")

    def test_no_candidate_returns_contract_error(self):
        response = self.client.get(
            "/api/v1/stations/nearby/",
            {
                "latitude": 35.1796,
                "longitude": 129.0756,
                "fuel_type": "gasoline",
                "radius_km": 1,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "NO_STATION_CANDIDATE")


class RecommendationQuoteAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_dummy_stations", verbosity=0)

    def setUp(self):
        self.client = APIClient()

    def test_travel_cost_recommendation_selects_lowest_effective_total_cost(self):
        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "gasoline",
                "target_liters": 50,
                "vehicle": {
                    "fuel_efficiency_kmpl": 10,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        recommendation = data["recommendation"]

        self.assertEqual(recommendation["station"]["name"], "SmartFuel 선릉점")
        self.assertEqual(recommendation["station"]["fuel_price_per_liter"], 1638)
        self.assertEqual(recommendation["cost_breakdown"]["refuel_cost"], 81900)
        self.assertEqual(recommendation["cost_breakdown"]["card_discount_amount"], 0)
        self.assertEqual(recommendation["cost_breakdown"]["travel_cost"], 314)
        self.assertEqual(recommendation["cost_breakdown"]["effective_total_cost"], 82214)
        self.assertIsNone(recommendation["selected_card"])
        self.assertEqual(data["meta"]["candidate_count"], 4)
        self.assertEqual(data["meta"]["distance_source"], "haversine")
        self.assertEqual(data["meta"]["map_display"]["coordinate_source"], "station_summary")
        self.assertEqual(data["meta"]["map_display"]["rank_source"], "backend_recommendation_order")
        self.assertFalse(data["meta"]["map_display"]["frontend_recalculation_allowed"])

    def test_recommendation_can_omit_candidates(self):
        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "diesel",
                "target_liters": 40,
                "vehicle": {
                    "fuel_efficiency_kmpl": 12,
                },
                "include_candidates": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["candidates"], [])

    def test_recommendation_invalid_target_liters_returns_contract_error(self):
        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "gasoline",
                "target_liters": 0,
                "vehicle": {
                    "fuel_efficiency_kmpl": 10,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_TARGET_LITERS")

    def test_recommendation_invalid_fuel_type_returns_contract_error(self):
        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "hydrogen",
                "target_liters": 50,
                "vehicle": {
                    "fuel_efficiency_kmpl": 10,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "UNSUPPORTED_FUEL_TYPE")

    def test_recommendation_missing_vehicle_efficiency_returns_contract_error(self):
        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "gasoline",
                "target_liters": 50,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "MISSING_VEHICLE_EFFICIENCY")

    def test_authenticated_user_can_use_saved_vehicle_profile(self):
        user = get_user_model().objects.create_user(username="saved-vehicle-user", password="pass12345")
        VehicleProfile.objects.create(
            user=user,
            fuel_type=FuelPrice.FuelType.GASOLINE,
            fuel_efficiency_kmpl="10.0",
            is_default=True,
        )
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "gasoline",
                "target_liters": 50,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        recommendation = response.json()["recommendation"]
        self.assertEqual(recommendation["cost_breakdown"]["travel_cost"], 314)

    def test_request_vehicle_overrides_saved_vehicle_profile(self):
        user = get_user_model().objects.create_user(username="override-vehicle-user", password="pass12345")
        VehicleProfile.objects.create(
            user=user,
            fuel_type=FuelPrice.FuelType.GASOLINE,
            fuel_efficiency_kmpl="5.0",
            is_default=True,
        )
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "gasoline",
                "target_liters": 50,
                "vehicle": {
                    "fuel_efficiency_kmpl": 10,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        recommendation = response.json()["recommendation"]
        self.assertEqual(recommendation["cost_breakdown"]["travel_cost"], 314)

    def test_recommendation_no_candidate_returns_contract_error(self):
        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 35.1796,
                    "longitude": 129.0756,
                },
                "fuel_type": "gasoline",
                "target_liters": 50,
                "radius_km": 1,
                "vehicle": {
                    "fuel_efficiency_kmpl": 10,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "NO_STATION_CANDIDATE")

    def test_confirmed_saved_card_policy_changes_recommendation_ranking(self):
        user = get_user_model().objects.create_user(username="ranking-card-user", password="pass12345")
        CardPolicy.objects.create(
            owner=user,
            card_name="GS Saver",
            issuer_name="Smart Bank",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=120,
            brand_scope="GS",
            max_discount_amount=6000,
            monthly_remaining_discount=6000,
            card_image_url="https://example.com/gs-saver.png",
        )
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "gasoline",
                "target_liters": 50,
                "vehicle": {
                    "fuel_efficiency_kmpl": 10,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        recommendation = response.json()["recommendation"]
        self.assertEqual(recommendation["station"]["brand"], "GS")
        self.assertEqual(recommendation["cost_breakdown"]["card_discount_amount"], 6000)
        self.assertEqual(recommendation["selected_card"]["card_name"], "GS Saver")
        self.assertEqual(recommendation["selected_card"]["card_image_url"], "https://example.com/gs-saver.png")
        self.assertIn("GS Saver", recommendation["reason"])
        self.assertIn("6000 KRW", recommendation["reason"])

    def test_distant_discounted_station_loses_when_travel_cost_exceeds_benefit(self):
        user = get_user_model().objects.create_user(username="distant-card-user", password="pass12345")
        near_station = GasStation.objects.create(
            external_station_id="QA-NEAR-001",
            name="QA Near Station",
            brand=GasStation.Brand.SK,
            address="QA near address",
            latitude="35.0000000",
            longitude="129.0000000",
        )
        distant_station = GasStation.objects.create(
            external_station_id="QA-DISTANT-001",
            name="QA Distant Discount Station",
            brand=GasStation.Brand.GS,
            address="QA distant address",
            latitude="35.2200000",
            longitude="129.0000000",
        )
        now = timezone.now()
        FuelPrice.objects.create(
            station=near_station,
            fuel_type=FuelPrice.FuelType.GASOLINE,
            price_per_liter=1000,
            collected_at=now,
        )
        FuelPrice.objects.create(
            station=distant_station,
            fuel_type=FuelPrice.FuelType.GASOLINE,
            price_per_liter=950,
            collected_at=now,
        )
        CardPolicy.objects.create(
            owner=user,
            card_name="Distant GS Saver",
            issuer_name="Smart Bank",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=1000,
            brand_scope="GS",
        )
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 35.0,
                    "longitude": 129.0,
                },
                "fuel_type": "gasoline",
                "target_liters": 50,
                "radius_km": 30,
                "vehicle": {
                    "fuel_efficiency_kmpl": 10,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        candidates = response.json()["candidates"]
        recommendation = response.json()["recommendation"]
        distant_candidate = next(
            item for item in candidates if item["station"]["station_id"] == distant_station.id
        )
        self.assertEqual(recommendation["station"]["station_id"], near_station.id)
        self.assertEqual(distant_candidate["cost_breakdown"]["card_discount_amount"], 1000)
        self.assertGreater(
            distant_candidate["cost_breakdown"]["travel_cost"],
            distant_candidate["cost_breakdown"]["card_discount_amount"],
        )

    def test_unverified_naver_card_policy_is_ignored_for_ranking(self):
        user = get_user_model().objects.create_user(username="unverified-card-user", password="pass12345")
        CardPolicy.objects.create(
            owner=user,
            card_name="Unverified GS Saver",
            issuer_name="Search Result Bank",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=1000,
            brand_scope="GS",
            source_type=CardPolicy.SourceType.NAVER_SEARCH,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "gasoline",
                "target_liters": 50,
                "vehicle": {
                    "fuel_efficiency_kmpl": 10,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        recommendation = response.json()["recommendation"]
        self.assertEqual(recommendation["station"]["brand"], "S_OIL")
        self.assertEqual(recommendation["cost_breakdown"]["card_discount_amount"], 0)
        self.assertIsNone(recommendation["selected_card"])

    def test_confirmed_discovered_card_policy_can_affect_ranking(self):
        user = get_user_model().objects.create_user(username="confirmed-discovery-user", password="pass12345")
        CardPolicy.objects.create(
            owner=user,
            card_name="Confirmed Discovery",
            issuer_name="Search Result Bank",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=7000,
            brand_scope="GS",
            source_type=CardPolicy.SourceType.NAVER_SEARCH,
            verification_status=CardPolicy.VerificationStatus.USER_CONFIRMED,
        )
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "gasoline",
                "target_liters": 50,
                "vehicle": {
                    "fuel_efficiency_kmpl": 10,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        recommendation = response.json()["recommendation"]
        self.assertEqual(recommendation["station"]["brand"], "GS")
        self.assertEqual(recommendation["selected_card"]["source_type"], "naver_search")
        self.assertEqual(recommendation["selected_card"]["verification_status"], "user_confirmed")

    def test_equal_effective_cost_uses_station_id_tiebreaker(self):
        first_station = GasStation.objects.create(
            external_station_id="TIE-001",
            name="Tie Station A",
            brand=GasStation.Brand.OTHER,
            address="Tie address A",
            latitude="35.0000000",
            longitude="129.0000000",
        )
        second_station = GasStation.objects.create(
            external_station_id="TIE-002",
            name="Tie Station B",
            brand=GasStation.Brand.OTHER,
            address="Tie address B",
            latitude="35.0000000",
            longitude="129.0000000",
        )
        now = timezone.now()
        for station in [first_station, second_station]:
            FuelPrice.objects.create(
                station=station,
                fuel_type=FuelPrice.FuelType.GASOLINE,
                price_per_liter=1000,
                collected_at=now,
            )

        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 35.0,
                    "longitude": 129.0,
                },
                "fuel_type": "gasoline",
                "target_liters": 10,
                "radius_km": 1,
                "vehicle": {
                    "fuel_efficiency_kmpl": 10,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        candidates = response.json()["candidates"]
        self.assertEqual(candidates[0]["station"]["station_id"], first_station.id)
        self.assertEqual(candidates[1]["station"]["station_id"], second_station.id)

    def test_response_uses_contract_rounding(self):
        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "gasoline",
                "target_liters": 33.333,
                "vehicle": {
                    "fuel_efficiency_kmpl": 12.345,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        recommendation = response.json()["recommendation"]
        cost_breakdown = recommendation["cost_breakdown"]
        self.assertEqual(cost_breakdown["target_liters"], 33.33)
        self.assertIsInstance(cost_breakdown["refuel_cost"], int)
        self.assertIsInstance(cost_breakdown["travel_cost"], int)
        self.assertIsInstance(cost_breakdown["effective_total_cost"], int)
        self.assertEqual(recommendation["station"]["distance_km"], round(recommendation["station"]["distance_km"], 2))

    def test_slice6_recommendation_reason_includes_required_explanation_fields(self):
        user = get_user_model().objects.create_user(username="slice6-reason-user", password="pass12345")
        CardPolicy.objects.create(
            owner=user,
            card_name="GS Saver",
            issuer_name="Smart Bank",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=120,
            brand_scope="GS",
            max_discount_amount=6000,
            monthly_remaining_discount=6000,
            card_image_url="https://example.com/gs-saver.png",
        )
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/v1/recommendations/quote/",
            {
                "location": {
                    "latitude": 37.501,
                    "longitude": 127.039,
                },
                "fuel_type": "gasoline",
                "target_liters": 50,
                "vehicle": {
                    "fuel_efficiency_kmpl": 10,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        recommendation = data["recommendation"]
        reason = recommendation["reason"]

        self.assertEqual(data["meta"]["algorithm_version"], "2026-05-19.v1-slice6-explanation")
        self.assertIn("리터당", reason)
        self.assertIn("기본 주유비", reason)
        self.assertIn("Smart Bank", reason)
        self.assertIn("GS Saver", reason)
        self.assertIn("6000 KRW", reason)
        self.assertIn("왕복 이동 비용", reason)
        self.assertIn("최종 예상 비용", reason)
        self.assertIn("절감액", reason)
        self.assertTrue("최저가 주유소" in reason or "가장 가까운 주유소" in reason)
        self.assertEqual(recommendation["selected_card"]["card_image_url"], "https://example.com/gs-saver.png")
