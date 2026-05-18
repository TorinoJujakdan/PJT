from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient


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
