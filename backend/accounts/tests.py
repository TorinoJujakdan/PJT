from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class AccountAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_signup_logs_in_and_returns_current_user(self):
        response = self.client.post(
            "/api/v1/accounts/signup/",
            {
                "username": "new-user",
                "email": "new@example.com",
                "password": "pass12345",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(response.json()["user"]["username"], "new-user")

        me = self.client.get("/api/v1/accounts/me/")
        self.assertTrue(me.json()["authenticated"])


    def test_signup_accepts_lightweight_password_and_logs_in(self):
        response = self.client.post(
            "/api/v1/accounts/signup/",
            {
                "username": "light-user",
                "email": "light@example.com",
                "password": "1234",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(response.json()["user"]["username"], "light-user")
        me = self.client.get("/api/v1/accounts/me/")
        self.assertTrue(me.json()["authenticated"])

    def test_login_and_logout_flow(self):
        get_user_model().objects.create_user(username="login-user", password="pass12345")

        login_response = self.client.post(
            "/api/v1/accounts/login/",
            {
                "username": "login-user",
                "password": "pass12345",
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.json()["authenticated"])
        self.assertEqual(login_response.json()["user"]["username"], "login-user")

        logout_response = self.client.post("/api/v1/accounts/logout/")
        self.assertEqual(logout_response.status_code, 204)

        me = self.client.get("/api/v1/accounts/me/")
        self.assertFalse(me.json()["authenticated"])

    def test_profile_patch_requires_authentication(self):
        response = self.client.patch("/api/v1/accounts/me/", {"email": "next@example.com"}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTHENTICATION_REQUIRED")

    def test_me_sets_csrf_cookie(self):
        response = self.client.get("/api/v1/accounts/me/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
