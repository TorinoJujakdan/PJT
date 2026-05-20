from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import VehicleProfile


class VehicleProfileAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username="vehicle-user", password="pass12345")

    def test_vehicle_profile_requires_authentication(self):
        response = self.client.get("/api/v1/me/vehicle/")

        self.assertEqual(response.status_code, 403)

    def test_put_creates_and_updates_default_vehicle_profile(self):
        self.client.force_authenticate(self.user)

        create_response = self.client.put(
            "/api/v1/me/vehicle/",
            {
                "fuel_type": "gasoline",
                "fuel_efficiency_kmpl": "12.5",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["vehicle"]["fuel_type"], "gasoline")
        self.assertEqual(VehicleProfile.objects.filter(user=self.user).count(), 1)

        update_response = self.client.put(
            "/api/v1/me/vehicle/",
            {
                "fuel_type": "diesel",
                "fuel_efficiency_kmpl": "15.0",
            },
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["vehicle"]["fuel_type"], "diesel")
        self.assertEqual(VehicleProfile.objects.filter(user=self.user).count(), 1)

    def test_invalid_efficiency_is_rejected(self):
        self.client.force_authenticate(self.user)

        response = self.client.put(
            "/api/v1/me/vehicle/",
            {
                "fuel_type": "gasoline",
                "fuel_efficiency_kmpl": "0.5",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_VEHICLE_PROFILE")
