from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import CommunityPost


class CommunityPostAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.author = User.objects.create_user(username="author", password="pass12345")
        self.other_user = User.objects.create_user(username="other", password="pass12345")

    def _create_post(self, **overrides):
        defaults = {
            "author": self.author,
            "title": "Useful community post",
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
        self.assertNotIn("station", list_response.json()["posts"][0])
        self.assertFalse(list_response.json()["posts"][0]["can_edit"])
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["id"], post.id)
        self.assertNotIn("station", detail_response.json())

    def test_anonymous_user_cannot_create_post(self):
        response = self.client.post(
            "/api/v1/community/posts/",
            {
                "title": "Anonymous post",
                "content": "Anonymous users cannot write.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTHENTICATION_REQUIRED")

    def test_authenticated_user_can_create_post_with_title_content_and_tags_only(self):
        self.client.force_authenticate(self.author)

        response = self.client.post(
            "/api/v1/community/posts/",
            {
                "title": "Fresh post",
                "content": "Only title, content, and tags are required for the community post.",
                "tags": ["mvp", "review", "mvp"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertNotIn("station", data)
        self.assertEqual(data["author"]["id"], self.author.id)
        self.assertEqual(data["tags"], ["mvp", "review"])
        self.assertTrue(data["can_edit"])
        self.assertEqual(CommunityPost.objects.count(), 1)

    def test_create_requires_only_title_and_content(self):
        self.client.force_authenticate(self.author)

        response = self.client.post(
            "/api/v1/community/posts/",
            {"title": "Missing content"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_COMMUNITY_POST")
        self.assertIn("content", response.json()["details"])

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

    def test_search_title_content_and_tag_filters(self):
        clean_post = self._create_post(
            title="Clean coffee stop",
            content="Good coffee near the route.",
            tags=["coffee", "clean"],
        )
        self._create_post(
            title="Quiet post",
            content="Different topic.",
            tags=["quiet"],
        )
        self._create_post(
            title="Unclean keyword should not match exact tag",
            content="This post has a different tag.",
            tags=["unclean"],
        )

        search_response = self.client.get("/api/v1/community/posts/", {"query": "coffee"})
        tag_response = self.client.get("/api/v1/community/posts/", {"tag": "coffee"})
        exact_tag_response = self.client.get("/api/v1/community/posts/", {"tag": "clean"})

        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(search_response.json()["meta"]["filters"], {"query": "coffee", "tag": None})
        removed_filter_name = "_".join(["station", "id"])
        self.assertNotIn(removed_filter_name, search_response.json()["meta"]["filters"])
        self.assertEqual([post["id"] for post in search_response.json()["posts"]], [clean_post.id])
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

    def test_community_post_model_has_no_station_recommendation_or_visit_verification_fields(self):
        field_names = {field.name for field in CommunityPost._meta.get_fields()}

        self.assertNotIn("station", field_names)
        self.assertNotIn("verified_visit", field_names)
        self.assertNotIn("visit_proof", field_names)
        self.assertNotIn("recommendation_score", field_names)
        self.assertNotIn("ranking_weight", field_names)
