from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from stations.models import GasStation

from .models import CommunityPost


class CommunityPostAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.author = User.objects.create_user(username="author", password="pass12345")
        self.other_user = User.objects.create_user(username="other", password="pass12345")
        self.station = GasStation.objects.create(
            external_station_id="COMMUNITY-STATION-001",
            name="Community Test Station",
            brand=GasStation.Brand.SK,
            address="Community test address",
            latitude="37.5010000",
            longitude="127.0390000",
        )
        self.other_station = GasStation.objects.create(
            external_station_id="COMMUNITY-STATION-002",
            name="Filtered Station",
            brand=GasStation.Brand.GS,
            address="Filtered address",
            latitude="37.5020000",
            longitude="127.0400000",
        )

    def _create_post(self, **overrides):
        defaults = {
            "station": self.station,
            "author": self.author,
            "title": "Useful station review",
            "content": "The pumps were clean and the staff was kind.",
            "tags": ["clean", "kind"],
        }
        defaults.update(overrides)
        return CommunityPost.objects.create(**defaults)

    def test_anonymous_user_can_list_and_read_posts(self):
        post = self._create_post()

        list_response = self.client.get("/api/v1/community/posts/")
        detail_response = self.client.get(f"/api/v1/community/posts/{post.id}/")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["meta"]["count"], 1)
        self.assertEqual(list_response.json()["posts"][0]["id"], post.id)
        self.assertFalse(list_response.json()["posts"][0]["can_edit"])
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["id"], post.id)

    def test_anonymous_user_cannot_create_post(self):
        response = self.client.post(
            "/api/v1/community/posts/",
            {
                "station_id": self.station.id,
                "title": "Anonymous post",
                "content": "Anonymous users cannot write.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTHENTICATION_REQUIRED")

    def test_authenticated_user_can_create_post_without_visit_verification(self):
        self.client.force_authenticate(self.author)

        response = self.client.post(
            "/api/v1/community/posts/",
            {
                "station_id": self.station.id,
                "title": "Fresh review",
                "content": "No visit proof is required for MVP.",
                "tags": ["mvp", "review", "mvp"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["station"]["station_id"], self.station.id)
        self.assertEqual(data["author"]["id"], self.author.id)
        self.assertEqual(data["tags"], ["mvp", "review"])
        self.assertTrue(data["can_edit"])
        self.assertEqual(CommunityPost.objects.count(), 1)

    def test_create_with_missing_station_returns_contract_error(self):
        self.client.force_authenticate(self.author)

        response = self.client.post(
            "/api/v1/community/posts/",
            {
                "station_id": 999999,
                "title": "Missing station",
                "content": "This should fail.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "STATION_NOT_FOUND")

    def test_author_can_update_post(self):
        post = self._create_post()
        self.client.force_authenticate(self.author)

        response = self.client.patch(
            f"/api/v1/community/posts/{post.id}/",
            {"title": "Updated title", "tags": ["updated"]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Updated title")
        self.assertEqual(response.json()["tags"], ["updated"])

    def test_author_can_delete_post(self):
        post = self._create_post()
        self.client.force_authenticate(self.author)

        response = self.client.delete(f"/api/v1/community/posts/{post.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(CommunityPost.objects.filter(id=post.id).exists())

    def test_non_author_update_returns_forbidden_not_not_found(self):
        post = self._create_post()
        self.client.force_authenticate(self.other_user)

        response = self.client.patch(
            f"/api/v1/community/posts/{post.id}/",
            {"title": "Unauthorized update"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "COMMUNITY_POST_FORBIDDEN")

    def test_non_author_delete_returns_forbidden_not_not_found(self):
        post = self._create_post()
        self.client.force_authenticate(self.other_user)

        response = self.client.delete(f"/api/v1/community/posts/{post.id}/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "COMMUNITY_POST_FORBIDDEN")
        self.assertTrue(CommunityPost.objects.filter(id=post.id).exists())

    def test_search_station_and_tag_filters(self):
        clean_post = self._create_post(
            title="Clean coffee stop",
            content="Good coffee near the station.",
            tags=["coffee", "clean"],
        )
        self._create_post(
            station=self.other_station,
            title="Quiet station",
            content="Different location.",
            tags=["quiet"],
        )
        self._create_post(
            title="Unclean keyword should not match",
            content="This post has a different tag.",
            tags=["unclean"],
        )

        search_response = self.client.get("/api/v1/community/posts/", {"query": "coffee"})
        station_response = self.client.get("/api/v1/community/posts/", {"station_id": self.station.id})
        tag_response = self.client.get("/api/v1/community/posts/", {"tag": "coffee"})
        exact_tag_response = self.client.get("/api/v1/community/posts/", {"tag": "clean"})

        self.assertEqual(search_response.status_code, 200)
        self.assertEqual([post["id"] for post in search_response.json()["posts"]], [clean_post.id])
        self.assertEqual(station_response.status_code, 200)
        self.assertEqual(station_response.json()["meta"]["count"], 2)
        self.assertEqual(tag_response.status_code, 200)
        self.assertEqual([post["id"] for post in tag_response.json()["posts"]], [clean_post.id])
        self.assertEqual(exact_tag_response.status_code, 200)
        self.assertEqual([post["id"] for post in exact_tag_response.json()["posts"]], [clean_post.id])

    def test_list_default_and_max_limit_are_bounded(self):
        for index in range(105):
            self._create_post(
                title=f"Bounded post {index:03d}",
                content="Bounded list test.",
                tags=["limit"],
            )

        default_response = self.client.get("/api/v1/community/posts/")
        max_response = self.client.get("/api/v1/community/posts/", {"limit": 200})

        self.assertEqual(default_response.status_code, 200)
        self.assertEqual(default_response.json()["meta"]["count"], 50)
        self.assertEqual(default_response.json()["meta"]["limit"], 50)
        self.assertEqual(max_response.status_code, 200)
        self.assertEqual(max_response.json()["meta"]["count"], 100)
        self.assertEqual(max_response.json()["meta"]["limit"], 100)

    def test_community_post_model_has_no_recommendation_or_visit_verification_fields(self):
        field_names = {field.name for field in CommunityPost._meta.get_fields()}

        self.assertNotIn("verified_visit", field_names)
        self.assertNotIn("visit_proof", field_names)
        self.assertNotIn("recommendation_score", field_names)
        self.assertNotIn("ranking_weight", field_names)
