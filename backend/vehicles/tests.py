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
                "name": "출퇴근차",
                "vehicle_type": "sedan",
                "fuel_type": "gasoline",
                "fuel_efficiency_kmpl": "12.5",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["vehicle"]["name"], "출퇴근차")
        self.assertEqual(create_response.json()["vehicle"]["vehicle_type"], "sedan")
        self.assertEqual(create_response.json()["vehicle"]["fuel_type"], "gasoline")
        self.assertEqual(VehicleProfile.objects.filter(user=self.user).count(), 1)

        update_response = self.client.put(
            "/api/v1/me/vehicle/",
            {
                "name": "주말 SUV",
                "vehicle_type": "suv",
                "fuel_type": "diesel",
                "fuel_efficiency_kmpl": "15.0",
            },
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["vehicle"]["name"], "주말 SUV")
        self.assertEqual(update_response.json()["vehicle"]["vehicle_type"], "suv")
        self.assertEqual(update_response.json()["vehicle"]["fuel_type"], "diesel")
        self.assertEqual(VehicleProfile.objects.filter(user=self.user).count(), 1)

    def test_invalid_efficiency_is_rejected(self):
        self.client.force_authenticate(self.user)

        response = self.client.put(
            "/api/v1/me/vehicle/",
            {
                "name": "연비 오류 차량",
                "vehicle_type": "compact",
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
            name="기존 차량",
            vehicle_type="sedan",
            fuel_type="gasoline",
            fuel_efficiency_kmpl="10.0",
            is_default=True,
        )

        response = self.client.patch(
            f"/api/v1/me/vehicles/{profile.id}/",
            {
                "name": "수정 차량",
                "vehicle_type": "sports",
                "fuel_type": "diesel",
                "fuel_efficiency_kmpl": "14.5",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["vehicle"]
        self.assertEqual(data["name"], "수정 차량")
        self.assertEqual(data["vehicle_type"], "sports")
        self.assertEqual(data["fuel_type"], "diesel")
        self.assertEqual(data["fuel_efficiency_kmpl"], "14.5")
        profile.refresh_from_db()
        self.assertEqual(profile.fuel_type, "diesel")

    def test_set_default_endpoint_unsets_other_defaults(self):
        self.client.force_authenticate(self.user)
        first = VehicleProfile.objects.create(
            user=self.user,
            name="첫 번째 차량",
            vehicle_type="compact",
            fuel_type="gasoline",
            fuel_efficiency_kmpl="10.0",
            is_default=True,
        )
        second = VehicleProfile.objects.create(
            user=self.user,
            name="두 번째 차량",
            vehicle_type="suv",
            fuel_type="diesel",
            fuel_efficiency_kmpl="14.0",
            is_default=False,
        )

        response = self.client.post(f"/api/v1/me/vehicles/{second.id}/set-default/")

        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

    def test_patch_cannot_unset_the_default_vehicle(self):
        self.client.force_authenticate(self.user)
        profile = VehicleProfile.objects.create(
            user=self.user,
            name="대표 차량",
            vehicle_type="sedan",
            fuel_type="gasoline",
            fuel_efficiency_kmpl="12.0",
            is_default=True,
        )

        response = self.client.patch(
            f"/api/v1/me/vehicles/{profile.id}/",
            {"is_default": False, "name": "이름만 수정"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertTrue(profile.is_default)
        self.assertEqual(profile.name, "이름만 수정")

    def test_patch_cannot_update_other_users_vehicle(self):
        other_user = get_user_model().objects.create_user(username="other-vehicle-user", password="pass12345")
        profile = VehicleProfile.objects.create(
            user=other_user,
            name="다른 사용자 차량",
            vehicle_type="large_rv",
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

    def test_post_requires_vehicle_name_and_type(self):
        self.client.force_authenticate(self.user)
        base = {"fuel_type": "gasoline", "fuel_efficiency_kmpl": "12.0"}

        missing_name = self.client.post(
            "/api/v1/me/vehicles/",
            {**base, "vehicle_type": "sedan"},
            format="json",
        )
        blank_name = self.client.post(
            "/api/v1/me/vehicles/",
            {**base, "name": "   ", "vehicle_type": "sedan"},
            format="json",
        )
        missing_type = self.client.post(
            "/api/v1/me/vehicles/",
            {**base, "name": "차량"},
            format="json",
        )

        self.assertEqual(missing_name.status_code, 400)
        self.assertEqual(blank_name.status_code, 400)
        self.assertEqual(missing_type.status_code, 400)

    def test_post_rejects_unknown_type_and_long_name(self):
        self.client.force_authenticate(self.user)

        unknown_type = self.client.post(
            "/api/v1/me/vehicles/",
            {
                "name": "미확인 차량",
                "vehicle_type": "truck",
                "fuel_type": "diesel",
                "fuel_efficiency_kmpl": "9.0",
            },
            format="json",
        )
        long_name = self.client.post(
            "/api/v1/me/vehicles/",
            {
                "name": "가" * 41,
                "vehicle_type": "large_rv",
                "fuel_type": "diesel",
                "fuel_efficiency_kmpl": "9.0",
            },
            format="json",
        )

        self.assertEqual(unknown_type.status_code, 400)
        self.assertEqual(long_name.status_code, 400)

    def test_post_trims_name_and_allows_duplicates(self):
        self.client.force_authenticate(self.user)
        payload = {
            "name": "  우리 차  ",
            "vehicle_type": "suv",
            "fuel_type": "gasoline",
            "fuel_efficiency_kmpl": "11.2",
        }

        first = self.client.post("/api/v1/me/vehicles/", payload, format="json")
        second = self.client.post("/api/v1/me/vehicles/", payload, format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["vehicle"]["name"], "우리 차")
        self.assertEqual(VehicleProfile.objects.filter(user=self.user, name="우리 차").count(), 2)

    def test_delete_default_promotes_next_vehicle(self):
        self.client.force_authenticate(self.user)
        first = VehicleProfile.objects.create(
            user=self.user,
            name="대표 차량",
            vehicle_type="sedan",
            fuel_type="gasoline",
            fuel_efficiency_kmpl="12.0",
            is_default=True,
        )
        second = VehicleProfile.objects.create(
            user=self.user,
            name="다음 차량",
            vehicle_type="compact",
            fuel_type="gasoline",
            fuel_efficiency_kmpl="14.0",
            is_default=False,
        )

        response = self.client.delete(f"/api/v1/me/vehicles/{first.id}/")

        self.assertEqual(response.status_code, 204)
        second.refresh_from_db()
        self.assertTrue(second.is_default)
