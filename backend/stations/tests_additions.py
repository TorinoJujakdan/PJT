from decimal import Decimal
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from cards.models import CardCatalog, CardPolicy
from cards.selenium_ingestion import ScrapedCardCandidate, save_candidates


class GeocodeProxyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_geocode_endpoint_returns_results_via_fallback(self):
        # Even without external API keys, the geocoding service must fall back gracefully to presets.
        response = self.client.get(
            "/api/v1/stations/geocode/",
            {"query": "서울시청"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        results = data["results"]
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["name"], "서울시청")
        self.assertAlmostEqual(results[0]["latitude"], 37.5665, places=4)
        self.assertAlmostEqual(results[0]["longitude"], 126.9780, places=4)

    def test_geocode_endpoint_missing_query_returns_400(self):
        response = self.client.get(
            "/api/v1/stations/geocode/",
            {"query": ""},
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["code"], "MISSING_QUERY")
        self.assertIn("message", data)


class CardAutoVerificationTests(TestCase):
    def test_save_candidates_auto_verifies_high_confidence_card(self):
        # 1. Candidate with high confidence (>= 0.85), valid discount_value (> 0) and non-empty name/issuer
        high_conf_candidate = ScrapedCardCandidate(
            card_name="KB국민 Easy All 카드",
            issuer_name="KB국민카드",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=Decimal("150"),
            confidence=Decimal("0.88"),
            source_url="https://card-search.naver.com/list#candidate-1",
        )

        # 2. Candidate with low confidence (< 0.85)
        low_conf_candidate = ScrapedCardCandidate(
            card_name="신한 Deep Oil 카드",
            issuer_name="신한카드",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
            confidence=Decimal("0.80"),
            source_url="https://card-search.naver.com/list#candidate-2",
        )

        # 3. Candidate with missing issuer name
        missing_issuer_candidate = ScrapedCardCandidate(
            card_name="우리카드 특별할인",
            issuer_name="",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("5000"),
            confidence=Decimal("0.90"),
            source_url="https://card-search.naver.com/list#candidate-3",
        )

        candidates = [high_conf_candidate, low_conf_candidate, missing_issuer_candidate]
        saved_cards = save_candidates(candidates, "https://card-search.naver.com/list")

        self.assertEqual(len(saved_cards), 3)

        # Verify high confidence card is ADMIN_VERIFIED
        card1 = CardCatalog.objects.get(source_url="https://card-search.naver.com/list#candidate-1")
        self.assertEqual(card1.verification_status, CardPolicy.VerificationStatus.ADMIN_VERIFIED)
        self.assertEqual(card1.card_name, "KB국민 Easy All 카드")

        # Verify low confidence card is UNVERIFIED
        card2 = CardCatalog.objects.get(source_url="https://card-search.naver.com/list#candidate-2")
        self.assertEqual(card2.verification_status, CardPolicy.VerificationStatus.UNVERIFIED)

        # Verify missing issuer card is UNVERIFIED
        card3 = CardCatalog.objects.get(source_url="https://card-search.naver.com/list#candidate-3")
        self.assertEqual(card3.verification_status, CardPolicy.VerificationStatus.UNVERIFIED)
