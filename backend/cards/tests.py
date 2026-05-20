from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from .models import CardCatalog, CardPolicy


class CardPolicyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username="card-user", password="pass12345")

    def test_card_policy_requires_authentication(self):
        response = self.client.get("/api/v1/me/cards/")

        self.assertEqual(response.status_code, 403)

    def test_create_manual_card_policy(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            "/api/v1/me/cards/",
            {
                "card_name": "Smart Oil Card",
                "issuer_name": "Smart Bank",
                "discount_type": "per_liter",
                "discount_value": "80",
                "brand_scope": "GS",
                "min_payment_amount": 30000,
                "max_discount_amount": 5000,
                "monthly_discount_limit": 12000,
                "monthly_remaining_discount": 12000,
                "card_image_url": "https://example.com/card.png",
                "source_url": "https://example.com/source",
                "source_title": "Smart Oil Card fuel benefit",
                "user_memo": "Manual policy",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["card_name"], "Smart Oil Card")
        self.assertEqual(data["issuer_name"], "Smart Bank")
        self.assertEqual(data["source_type"], "manual")
        self.assertEqual(data["verification_status"], "user_confirmed")
        self.assertEqual(data["card_image_url"], "https://example.com/card.png")
        self.assertEqual(CardPolicy.objects.filter(owner=self.user, is_active=True).count(), 1)

    def test_list_only_my_active_card_policies(self):
        other_user = get_user_model().objects.create_user(username="other-user", password="pass12345")
        CardPolicy.objects.create(
            owner=self.user,
            card_name="My Card",
            issuer_name="Mine",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=80,
        )
        CardPolicy.objects.create(
            owner=other_user,
            card_name="Other Card",
            issuer_name="Other",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=100,
        )

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/me/cards/")

        self.assertEqual(response.status_code, 200)
        cards = response.json()["cards"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["card_name"], "My Card")

    def test_delete_card_policy_soft_deletes_owned_policy(self):
        policy = CardPolicy.objects.create(
            owner=self.user,
            card_name="Delete Card",
            issuer_name="Mine",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=1000,
        )

        self.client.force_authenticate(self.user)
        response = self.client.delete(f"/api/v1/me/cards/{policy.id}/")

        self.assertEqual(response.status_code, 204)
        policy.refresh_from_db()
        self.assertFalse(policy.is_active)

    def test_patch_card_policy_updates_owned_policy(self):
        policy = CardPolicy.objects.create(
            owner=self.user,
            card_name="Before Card",
            issuer_name="Mine",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=80,
            brand_scope="all",
        )

        self.client.force_authenticate(self.user)
        response = self.client.patch(
            f"/api/v1/me/cards/{policy.id}/",
            {
                "card_name": "After Card",
                "discount_type": "percentage",
                "discount_value": "10",
                "brand_scope": "GS",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["card_name"], "After Card")
        self.assertEqual(data["discount_type"], "percentage")
        self.assertEqual(data["brand_scope"], "GS")

    def test_delete_missing_card_policy_returns_contract_error(self):
        self.client.force_authenticate(self.user)

        response = self.client.delete("/api/v1/me/cards/999/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "CARD_POLICY_NOT_FOUND")

    def test_discovery_requires_allowed_selenium_domain(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(
            "/api/v1/cards/discovery/",
            {
                "query": "GS칼텍스 주유 할인 카드",
                "issuer_name": "Smart Bank",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["candidates"], [])
        self.assertEqual(data["meta"]["source_type"], "selenium")
        self.assertTrue(data["meta"]["requires_user_confirmation"])
        self.assertEqual(data["meta"]["provider_status"], "allowlist_required")
        self.assertEqual(data["meta"]["allowed_domains"], ["card-search.naver.com"])

    def test_discovery_accepts_user_approved_naver_card_search_domain(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(
            "/api/v1/cards/discovery/",
            {
                "query": "fuel card",
                "domain": "https://card-search.naver.com/list?benefitCategoryIds=1",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["candidates"], [])
        self.assertEqual(data["meta"]["source_type"], "selenium")
        self.assertEqual(data["meta"]["provider_status"], "not_implemented")
        self.assertIn("card-search.naver.com", data["meta"]["allowed_domains"])

    def test_discovery_rejects_domain_outside_allowlist(self):
        self.client.force_authenticate(self.user)

        with patch.dict("os.environ", {"CARD_INGESTION_ALLOWED_DOMAINS": "allowed.example.com"}):
            response = self.client.get(
                "/api/v1/cards/discovery/",
                {
                    "query": "fuel card",
                    "domain": "https://not-allowed.example.com/cards",
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["candidates"], [])
        self.assertEqual(data["meta"]["source_type"], "selenium")
        self.assertEqual(data["meta"]["provider_status"], "domain_not_allowed")
        self.assertEqual(data["meta"]["allowed_domains"], ["allowed.example.com", "card-search.naver.com"])

    def test_invalid_percentage_discount_is_rejected(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            "/api/v1/me/cards/",
            {
                "card_name": "Broken Card",
                "issuer_name": "Broken Bank",
                "discount_type": "percentage",
                "discount_value": "101",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_CARD_POLICY")

    def test_catalog_search_returns_unverified_candidates(self):
        CardCatalog.objects.create(
            card_name="KB국민 굿데이카드",
            issuer_name="KB국민카드",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=60,
            source_url="https://card-search.naver.com/card/1",
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )
        CardCatalog.objects.create(
            card_name="신한카드 Deep Oil",
            issuer_name="신한카드",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=10,
            source_url="https://card-search.naver.com/card/2",
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/cards/catalog/", {"query": "굿데이"})

        self.assertEqual(response.status_code, 200)
        cards = response.json()["cards"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["card_name"], "KB국민 굿데이카드")
        self.assertEqual(cards[0]["verification_status"], "unverified")

    def test_create_card_policy_from_catalog_confirms_user_card(self):
        catalog = CardCatalog.objects.create(
            card_name="KB국민 굿데이카드",
            issuer_name="KB국민카드",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=60,
            brand_scope="all",
            source_url="https://card-search.naver.com/card/1",
            source_title="KB국민 굿데이카드",
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/me/cards/from-catalog/",
            {
                "catalog_card_id": catalog.id,
                "monthly_remaining_discount": 10000,
                "user_memo": "확인 후 저장",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["card_name"], "KB국민 굿데이카드")
        self.assertEqual(data["source_type"], "selenium")
        self.assertEqual(data["verification_status"], "user_confirmed")
        self.assertEqual(CardPolicy.objects.filter(owner=self.user).count(), 1)

    def test_create_card_policy_from_catalog_allows_user_overrides(self):
        catalog = CardCatalog.objects.create(
            card_name="삼성카드 taptap S",
            issuer_name="삼성카드",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=2000,
            brand_scope="all",
            source_url="https://card-search.naver.com/card/2",
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/me/cards/from-catalog/",
            {
                "catalog_card_id": catalog.id,
                "discount_type": "percentage",
                "discount_value": "5",
                "brand_scope": "GS",
                "max_discount_amount": 5000,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        policy = CardPolicy.objects.get(owner=self.user)
        self.assertEqual(policy.discount_type, CardPolicy.DiscountType.PERCENTAGE)
        self.assertEqual(policy.discount_value, 5)
        self.assertEqual(policy.brand_scope, "GS")
        self.assertEqual(policy.max_discount_amount, 5000)

    def test_create_card_policy_from_catalog_rejects_invalid_percentage_override(self):
        catalog = CardCatalog.objects.create(
            card_name="Broken Percent",
            issuer_name="Test",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=50,
            source_url="https://card-search.naver.com/card/3",
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/me/cards/from-catalog/",
            {
                "catalog_card_id": catalog.id,
                "discount_type": "percentage",
                "discount_value": "120",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_CARD_POLICY")

    def test_create_card_policy_from_missing_catalog_returns_404(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            "/api/v1/me/cards/from-catalog/",
            {"catalog_card_id": 999},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "CARD_CATALOG_NOT_FOUND")
