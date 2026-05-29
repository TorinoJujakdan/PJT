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

    def test_patch_updates_owned_vehicle_profile(self):
        self.client.force_authenticate(self.user)
        profile = VehicleProfile.objects.create(
            user=self.user,
            fuel_type="gasoline",
            fuel_efficiency_kmpl="10.0",
            is_default=True,
        )

        response = self.client.patch(
            f"/api/v1/me/vehicles/{profile.id}/",
            {
                "fuel_type": "diesel",
                "fuel_efficiency_kmpl": "14.5",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["vehicle"]
        self.assertEqual(data["fuel_type"], "diesel")
        self.assertEqual(data["fuel_efficiency_kmpl"], "14.5")
        profile.refresh_from_db()
        self.assertEqual(profile.fuel_type, "diesel")

    def test_patch_default_vehicle_unsets_other_defaults(self):
        self.client.force_authenticate(self.user)
        first = VehicleProfile.objects.create(
            user=self.user,
            fuel_type="gasoline",
            fuel_efficiency_kmpl="10.0",
            is_default=True,
        )
        second = VehicleProfile.objects.create(
            user=self.user,
            fuel_type="diesel",
            fuel_efficiency_kmpl="14.0",
            is_default=False,
        )

        response = self.client.patch(
            f"/api/v1/me/vehicles/{second.id}/",
            {"is_default": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

    def test_patch_cannot_update_other_users_vehicle(self):
        other_user = get_user_model().objects.create_user(username="other-vehicle-user", password="pass12345")
        profile = VehicleProfile.objects.create(
            user=other_user,
            fuel_type="gasoline",
            fuel_efficiency_kmpl="10.0",
            is_default=True,
        )
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            f"/api/v1/me/vehicles/{profile.id}/",
            {"fuel_efficiency_kmpl": "20.0"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
