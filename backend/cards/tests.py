from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from .models import CardBenefitTier, CardCatalog, CardPolicy


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

    def test_list_linked_catalog_card_exposes_tier_as_effective_benefit(self):
        catalog = CardCatalog.objects.create(
            card_name="Tier Card",
            issuer_name="Tier Bank",
            source_url="https://card-search.naver.com/card/tier",
        )
        CardBenefitTier.objects.create(
            card_catalog=catalog,
            fuel_type="ALL",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=90,
            brand_scope="GS",
            min_payment_amount=30000,
            monthly_discount_limit=15000,
        )
        CardPolicy.objects.create(
            owner=self.user,
            linked_catalog=catalog,
            card_name="Tier Card",
            issuer_name="Tier Bank",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=0,
            source_type=CardPolicy.SourceType.CATALOG,
        )

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/me/cards/")

        self.assertEqual(response.status_code, 200)
        card = response.json()["cards"][0]
        self.assertEqual(card["effective_benefit"]["discount_type"], "per_liter")
        self.assertEqual(card["effective_benefit"]["discount_value"], "90.00")
        self.assertEqual(card["effective_benefit"]["brand_scope"], "GS")
        self.assertEqual(card["catalog_benefit_tiers"][0]["monthly_discount_limit"], 15000)

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
        catalog1 = CardCatalog.objects.create(
            card_name="KB국민 굿데이카드",
            issuer_name="KB국민카드",
            source_url="https://card-search.naver.com/card/1",
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )
        CardBenefitTier.objects.create(
            card_catalog=catalog1,
            fuel_type="ALL",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=60,
        )
        catalog2 = CardCatalog.objects.create(
            card_name="신한카드 Deep Oil",
            issuer_name="신한카드",
            source_url="https://card-search.naver.com/card/2",
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )
        CardBenefitTier.objects.create(
            card_catalog=catalog2,
            fuel_type="ALL",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=10,
        )

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/cards/catalog/", {"query": "굿데이"})

        self.assertEqual(response.status_code, 200)
        cards = response.json()["cards"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["card_name"], "KB국민 굿데이카드")
        self.assertEqual(cards[0]["verification_status"], "unverified")
        self.assertEqual(cards[0]["effective_benefit"]["discount_type"], "per_liter")
        self.assertEqual(cards[0]["effective_benefit"]["discount_value"], "60.00")

    def test_catalog_search_suppresses_unrealistic_percentage_effective_benefit(self):
        catalog = CardCatalog.objects.create(
            card_name="삼성 iD SELECT ALL 카드",
            issuer_name="삼성카드",
            source_url="https://card-search.naver.com/card/select-all",
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )
        CardBenefitTier.objects.create(
            card_catalog=catalog,
            fuel_type="ALL",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=100,
        )

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/cards/catalog/", {"query": "SELECT ALL"})

        self.assertEqual(response.status_code, 200)
        cards = response.json()["cards"]
        self.assertEqual(len(cards), 1)
        self.assertIsNone(cards[0]["effective_benefit"])

    def test_create_card_policy_from_catalog_confirms_user_card(self):
        catalog = CardCatalog.objects.create(
            card_name="KB국민 굿데이카드",
            issuer_name="KB국민카드",
            source_url="https://card-search.naver.com/card/1",
            source_title="KB국민 굿데이카드",
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )
        CardBenefitTier.objects.create(
            card_catalog=catalog,
            fuel_type="ALL",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=60,
            brand_scope="all",
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
        self.assertEqual(data["source_type"], "catalog")
        self.assertEqual(data["verification_status"], "user_confirmed")
        self.assertEqual(data["discount_value"], "60.00")
        self.assertEqual(data["effective_benefit"]["discount_value"], "60.00")
        self.assertEqual(CardPolicy.objects.filter(owner=self.user).count(), 1)

    def test_create_card_policy_from_catalog_allows_user_overrides(self):
        catalog = CardCatalog.objects.create(
            card_name="삼성카드 taptap S",
            issuer_name="삼성카드",
            source_url="https://card-search.naver.com/card/2",
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )
        CardBenefitTier.objects.create(
            card_catalog=catalog,
            fuel_type="ALL",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=2000,
            brand_scope="all",
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
        self.assertEqual(response.json()["effective_benefit"]["discount_type"], "percentage")
        self.assertEqual(response.json()["effective_benefit"]["discount_value"], "5.00")

    def test_create_card_policy_from_catalog_rejects_invalid_percentage_override(self):
        catalog = CardCatalog.objects.create(
            card_name="Broken Percent",
            issuer_name="Test",
            source_url="https://card-search.naver.com/card/3",
        )
        CardBenefitTier.objects.create(
            card_catalog=catalog,
            fuel_type="ALL",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=50,
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

    def test_create_card_policy_from_held_catalog_requires_manual_benefit_fields(self):
        catalog = CardCatalog.objects.create(
            card_name="Held Card",
            issuer_name="Held Bank",
            source_url="https://card-search.naver.com/card/held",
            normalized_data={"quality": {"warnings": ["fuel_benefit_relevance_missing"]}},
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/me/cards/from-catalog/",
            {"catalog_card_id": catalog.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_CARD_POLICY")
        self.assertEqual(CardPolicy.objects.filter(owner=self.user).count(), 0)

    def test_create_card_policy_from_held_catalog_accepts_manual_benefit_fields(self):
        catalog = CardCatalog.objects.create(
            card_name="Held Card",
            issuer_name="Held Bank",
            source_url="https://card-search.naver.com/card/held-manual",
            normalized_data={"quality": {"warnings": ["fuel_benefit_relevance_missing"]}},
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/me/cards/from-catalog/",
            {
                "catalog_card_id": catalog.id,
                "discount_type": "per_liter",
                "discount_value": "70",
                "brand_scope": "GS",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        policy = CardPolicy.objects.get(owner=self.user)
        self.assertEqual(policy.linked_catalog, catalog)
        self.assertEqual(policy.discount_value, 70)
        self.assertEqual(policy.verification_status, "user_confirmed")

    def test_create_card_policy_from_held_catalog_does_not_inherit_stale_tier_limits(self):
        catalog = CardCatalog.objects.create(
            card_name="Held Card",
            issuer_name="Held Bank",
            source_url="https://card-search.naver.com/card/held-stale",
            normalized_data={"quality": {"warnings": ["fuel_benefit_relevance_missing"]}},
        )
        CardBenefitTier.objects.create(
            card_catalog=catalog,
            fuel_type="ALL",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=30,
            brand_scope="all",
            min_payment_amount=300000,
            monthly_discount_limit=50000,
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/me/cards/from-catalog/",
            {
                "catalog_card_id": catalog.id,
                "discount_type": "per_liter",
                "discount_value": "70",
                "brand_scope": "GS",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        policy = CardPolicy.objects.get(owner=self.user)
        self.assertEqual(policy.discount_type, CardPolicy.DiscountType.PER_LITER)
        self.assertEqual(policy.discount_value, 70)
        self.assertEqual(policy.brand_scope, "GS")
        self.assertIsNone(policy.min_payment_amount)
        self.assertIsNone(policy.monthly_discount_limit)

    def test_create_card_policy_from_missing_catalog_returns_404(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            "/api/v1/me/cards/from-catalog/",
            {"catalog_card_id": 999},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "CARD_CATALOG_NOT_FOUND")


class CardBenefitDataQualityTests(TestCase):
    def test_normalize_brand_scope_expands_four_major_station_scope(self):
        from cards.brand_scope import normalize_brand_scope

        result = normalize_brand_scope("4대 주유소")

        self.assertEqual(result.scope, "SK,GS,S-OIL,HD현대오일뱅크")
        self.assertTrue(result.inferred)
        self.assertEqual(result.reason, "expanded_four_major_stations")

    def test_normalize_brand_scope_keeps_all_scope_canonical(self):
        from cards.brand_scope import normalize_brand_scope

        result = normalize_brand_scope("ALL")

        self.assertEqual(result.scope, "all")
        self.assertFalse(result.inferred)

    def test_unrealistic_percentage_fuel_benefit_is_not_usable(self):
        from cards.benefit_safety import is_usable_fuel_benefit

        self.assertFalse(is_usable_fuel_benefit("percentage", 40, "주유 40% 할인"))

    def test_normalize_card_fixture_dry_run_writes_report_without_mutating_fixture(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from django.core.management import call_command

        fixture = [
            {
                "model": "cards.cardbenefittier",
                "pk": 1,
                "fields": {
                    "card_catalog": 1,
                    "fuel_type": "ALL",
                    "min_performance_amount": 0,
                    "discount_type": "percentage",
                    "discount_value": "40.00",
                    "brand_scope": "4대 주유소",
                },
            }
        ]
        with TemporaryDirectory() as tmpdir:
            fixture_path = Path(tmpdir) / "card_data.json"
            report_path = Path(tmpdir) / "report.json"
            fixture_path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")

            call_command(
                "normalize_card_fuel_benefits",
                "--fixture",
                str(fixture_path),
                "--report",
                str(report_path),
                "--dry-run",
            )

            saved_fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_fixture[0]["fields"]["brand_scope"], "4대 주유소")
            self.assertEqual(report["summary"]["normalized_brand_scopes"], 1)
            self.assertEqual(report["summary"]["suspicious_tiers"], 1)
            self.assertEqual(report["items"][0]["normalized_brand_scope"], "SK,GS,S-OIL,HD현대오일뱅크")
            self.assertTrue(report["items"][0]["brand_scope_inferred"])
