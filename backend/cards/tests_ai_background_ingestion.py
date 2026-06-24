from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from cards.gemini_client import GeminiRequestError
from cards.models import CardCatalog, CardIngestionTask, CardPolicy
from cards.tests_ai_normalization import _candidate, _valid_llm_payload
from cards.views import run_background_ingestion
from cards.selenium_ingestion import ScrapedCardCandidate


class BackgroundIngestionTests(TestCase):
    def test_successful_background_ingestion_persists_success_status_and_results(self) -> None:
        user = get_user_model().objects.create_user(username="success-user", password="pass12345")
        task = CardIngestionTask.objects.create(owner=user, query="fuel card")
        candidate = _candidate(raw_summary="Card A\nFuel\n60 won per liter discount\nGS Caltex")

        with (
            patch("cards.views.scrape_card_search_candidates", return_value=[candidate]),
            patch(
                "cards.views.normalize_card_fuel_benefit",
                return_value=_valid_llm_payload(CardPolicy.DiscountType.PER_LITER, "60"),
            ),
            patch("cards.selenium_ingestion.fetch_remote_image", return_value=(None, "")),
        ):
            run_background_ingestion(task.id, "fuel card")

        task.refresh_from_db()
        self.assertEqual(task.status, CardIngestionTask.Status.SUCCESS)
        self.assertEqual(CardCatalog.objects.count(), 1)
        self.assertEqual(task.results.count(), 1)

    def test_gemini_failure_marks_task_failed_without_heuristic_fallback(self) -> None:
        user = get_user_model().objects.create_user(username="ingestion-user", password="pass12345")
        task = CardIngestionTask.objects.create(owner=user, query="fuel card")
        candidate = _candidate(raw_summary="Card A\nFuel\n60 won per liter discount\nGS Caltex")

        with (
            patch("cards.views.scrape_card_search_candidates", return_value=[candidate]),
            patch(
                "cards.views.save_ai_normalized_candidates",
                side_effect=GeminiRequestError("temporary Gemini failure"),
            ),
        ):
            run_background_ingestion(task.id, "fuel card")

        task.refresh_from_db()
        self.assertEqual(task.status, CardIngestionTask.Status.FAILED)
        self.assertIn("temporary Gemini failure", task.error_message)
        self.assertEqual(CardCatalog.objects.count(), 0)

    def test_partial_background_gemini_failure_rolls_back_saved_catalog_rows(self) -> None:
        user = get_user_model().objects.create_user(username="rollback-user", password="pass12345")
        task = CardIngestionTask.objects.create(owner=user, query="fuel card")
        first_candidate = _candidate(raw_summary="Card A\nFuel\n60 won per liter discount\nGS Caltex")
        second_candidate = ScrapedCardCandidate(
            card_name="Card B",
            issuer_name="Issuer",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("10000"),
            raw_summary="Card B\nFuel\n10000 won discount\nGS Caltex",
            source_url="https://card-search.naver.com/card/b",
            confidence=Decimal("0.90"),
        )

        with (
            patch("cards.views.scrape_card_search_candidates", return_value=[first_candidate, second_candidate]),
            patch(
                "cards.views.normalize_card_fuel_benefit",
                side_effect=[
                    _valid_llm_payload(CardPolicy.DiscountType.PER_LITER, "60"),
                    GeminiRequestError("temporary Gemini failure after first save"),
                ],
            ),
            patch("cards.selenium_ingestion.fetch_remote_image", return_value=(None, "")),
        ):
            run_background_ingestion(task.id, "fuel card")

        task.refresh_from_db()
        self.assertEqual(task.status, CardIngestionTask.Status.FAILED)
        self.assertIn("temporary Gemini failure after first save", task.error_message)
        self.assertEqual(CardCatalog.objects.count(), 0)
        self.assertEqual(task.results.count(), 0)
