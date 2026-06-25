from __future__ import annotations

from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command, load_command_class
from django.test import TestCase

from cards.ai_chunks import compute_raw_hash
from cards.ai_normalization import save_ai_normalized_candidates
from cards.gemini_client import (
    GeminiClientConfig,
    GeminiRequestError,
    _build_request_payload,
    build_gemini_normalization_prompt,
    estimate_gemini_cost,
)
from cards.llm_fuel_extraction import build_line_numbered_document, validate_llm_fuel_payload
from cards.models import CardBenefitTier, CardCatalog, CardPolicy
from cards.selenium_ingestion import ScrapedCardCandidate, run_api_fallback_scraper


class LlmFuelExtractionTests(TestCase):
    def test_validate_llm_payload_accepts_grounded_fuel_discount(self) -> None:
        raw_text = "Card A\nFuel\n60 won per liter discount\nGS Caltex"
        document = build_line_numbered_document(raw_text)
        payload = _valid_llm_payload(discount_type=CardPolicy.DiscountType.PER_LITER, discount_value="60")

        result = validate_llm_fuel_payload(document, payload)

        self.assertIsNotNone(result.tier_data)
        self.assertEqual(result.tier_data.discount_type, CardPolicy.DiscountType.PER_LITER)
        self.assertEqual(result.tier_data.discount_value, Decimal("60"))
        self.assertEqual(result.warnings, [])

    def test_validate_llm_payload_rejects_ungrounded_discount_value(self) -> None:
        raw_text = "Card A\nFuel\n60 won per liter discount\nGS Caltex"
        document = build_line_numbered_document(raw_text)
        payload = _valid_llm_payload(discount_type=CardPolicy.DiscountType.PER_LITER, discount_value="200")

        result = validate_llm_fuel_payload(document, payload)

        self.assertIsNone(result.tier_data)
        self.assertIn("discount_value_not_supported_by_evidence", result.warnings)

    def test_validate_llm_payload_preserves_gemini_usage_metadata(self) -> None:
        raw_text = "Card A\nFuel\n60 won per liter discount\nGS Caltex"
        document = build_line_numbered_document(raw_text)
        payload = _valid_llm_payload(discount_type=CardPolicy.DiscountType.PER_LITER, discount_value="60")
        payload["model"] = "gemini-3.5-flash"
        payload["usage_metadata"] = {"promptTokenCount": 100, "candidatesTokenCount": 25}
        payload["cost_estimate"] = {"total_cost_usd": "0.000375"}

        result = validate_llm_fuel_payload(document, payload)

        self.assertEqual(result.normalized_payload["model"], "gemini-3.5-flash")
        self.assertEqual(result.normalized_payload["usage_metadata"]["promptTokenCount"], 100)
        self.assertEqual(result.normalized_payload["cost_estimate"]["total_cost_usd"], "0.000375")

    def test_gemini_cost_estimate_includes_thinking_tokens(self) -> None:
        usage_metadata = {
            "promptTokenCount": 1200,
            "candidatesTokenCount": 400,
            "thoughtsTokenCount": 100,
        }

        estimate = estimate_gemini_cost("gemini-3.5-flash", usage_metadata)

        self.assertEqual(estimate["candidate_tokens"], 400)
        self.assertEqual(estimate["thinking_tokens"], 100)
        self.assertEqual(estimate["output_tokens"], 500)
        self.assertEqual(estimate["total_cost_usd"], "0.0063")

    def test_request_payload_uses_gemini_compatible_inline_schema(self) -> None:
        config = GeminiClientConfig(
            api_key="test-key",
            model="gemini-3.5-flash",
            base_url="https://example.test",
            timeout_seconds=30,
            max_output_tokens=128,
        )

        payload = _build_request_payload("prompt", config)
        response_schema = payload["generationConfig"]["responseSchema"]

        for unsupported_key in ("$defs", "$ref", "$schema", "default", "pattern", "title", "anyOf"):
            self.assertFalse(_contains_key(response_schema, unsupported_key), unsupported_key)
        card_schema = response_schema["properties"]["card"]
        self.assertEqual(card_schema["properties"]["name"]["type"], "string")
        benefit_schema = response_schema["properties"]["benefits"]["items"]
        self.assertEqual(benefit_schema["properties"]["discount_value"]["type"], "number")
        self.assertTrue(benefit_schema["properties"]["min_payment_amount"]["nullable"])


class AiNormalizedCandidateSaveTests(TestCase):
    def setUp(self) -> None:
        self._image_fetch_patch = patch(
            "cards.selenium_ingestion.fetch_remote_image",
            return_value=(None, ""),
        )
        self._image_fetch_patch.start()

    def tearDown(self) -> None:
        self._image_fetch_patch.stop()

    def test_save_ai_normalized_candidates_stores_only_validated_llm_tier(self) -> None:
        candidate = _candidate(raw_summary="Card A\nFuel\n10000 won discount\nGS Caltex")
        payload = _valid_llm_payload(discount_type=CardPolicy.DiscountType.FIXED_AMOUNT, discount_value="10000")
        payload["model"] = "gemini-3.5-flash"
        payload["usage_metadata"] = {"promptTokenCount": 1200, "candidatesTokenCount": 400}
        payload["cost_estimate"] = {"total_cost_usd": "0.0054"}

        saved = save_ai_normalized_candidates(
            [candidate],
            source_url="https://card-search.naver.com/list?benefitCategoryIds=1",
            normalizer=lambda _candidate: payload,
        )

        self.assertEqual(len(saved), 1)
        catalog = CardCatalog.objects.get()
        tier = CardBenefitTier.objects.get(card_catalog=catalog)
        self.assertEqual(tier.discount_type, CardPolicy.DiscountType.FIXED_AMOUNT)
        self.assertEqual(tier.discount_value, Decimal("10000.00"))
        self.assertEqual(catalog.raw_hash, compute_raw_hash(candidate.raw_summary))
        self.assertEqual(catalog.normalized_data["usage_metadata"]["promptTokenCount"], 1200)
        self.assertEqual(catalog.normalized_data["cost_estimate"]["total_cost_usd"], "0.0054")

    def test_invalid_llm_tier_does_not_fall_back_to_scraped_candidate_tier(self) -> None:
        candidate = _candidate(raw_summary="Card A\nFuel\n60 won per liter discount\nGS Caltex")
        invalid_payload = _valid_llm_payload(discount_type=CardPolicy.DiscountType.PER_LITER, discount_value="200")

        saved = save_ai_normalized_candidates(
            [candidate],
            source_url="https://card-search.naver.com/list?benefitCategoryIds=1",
            normalizer=lambda _candidate: invalid_payload,
        )

        self.assertEqual(len(saved), 1)
        catalog = CardCatalog.objects.get()
        self.assertFalse(CardBenefitTier.objects.filter(card_catalog=catalog).exists())
        self.assertIn("discount_value_not_supported_by_evidence", catalog.normalized_data["quality"]["warnings"])
        self.assertEqual(catalog.normalized_data["benefits"], [])
        self.assertEqual(len(catalog.normalized_data["raw_llm_benefits"]), 1)

    def test_invalid_llm_tier_removes_existing_stale_tiers(self) -> None:
        candidate = _candidate(raw_summary="Card A\nFuel\n60 won per liter discount\nGS Caltex")
        valid_payload = _valid_llm_payload(discount_type=CardPolicy.DiscountType.PER_LITER, discount_value="60")
        invalid_payload = _valid_llm_payload(discount_type=CardPolicy.DiscountType.PER_LITER, discount_value="200")

        save_ai_normalized_candidates(
            [candidate],
            source_url="https://card-search.naver.com/list?benefitCategoryIds=1",
            normalizer=lambda _candidate: valid_payload,
        )
        save_ai_normalized_candidates(
            [candidate],
            source_url="https://card-search.naver.com/list?benefitCategoryIds=1",
            normalizer=lambda _candidate: invalid_payload,
        )

        catalog = CardCatalog.objects.get()
        self.assertFalse(CardBenefitTier.objects.filter(card_catalog=catalog).exists())


class IngestCardSearchAiCommandTests(TestCase):
    def test_legacy_and_gemini_management_commands_load(self) -> None:
        for command_name in ("check_gms_key", "ingest_card_search", "ingest_card_search_ai"):
            command = load_command_class("cards", command_name)
            self.assertIsNotNone(command)

    def test_fallback_candidate_summary_is_accepted_for_gemini_prompt(self) -> None:
        candidate = run_api_fallback_scraper(limit=1)[0]

        prompt = build_gemini_normalization_prompt(candidate)

        self.assertIn(candidate.raw_summary, prompt)

    def test_dry_run_normalizes_without_saving_catalog_rows(self) -> None:
        candidate = _candidate(raw_summary="Card A\nFuel\n60 won per liter discount\nGS Caltex")
        output = StringIO()

        with (
            patch(
                "cards.management.commands.ingest_card_search_ai.scrape_card_search_candidates",
                return_value=[candidate],
            ),
            patch(
                "cards.management.commands.ingest_card_search_ai.normalize_card_fuel_benefit",
                return_value=_valid_llm_payload(CardPolicy.DiscountType.PER_LITER, "60"),
            ),
        ):
            call_command("ingest_card_search_ai", "--dry-run", stdout=output)

        self.assertIn(compute_raw_hash(candidate.raw_summary), output.getvalue())
        self.assertEqual(CardCatalog.objects.count(), 0)

    def test_request_error_isolated_per_candidate(self) -> None:
        failing_candidate = _candidate(raw_summary="Card A\nFuel\n60 won per liter discount\nGS Caltex")
        saved_candidate = ScrapedCardCandidate(
            card_name="Card B",
            issuer_name="Issuer",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("10000"),
            raw_summary="Card B\nFuel\n10000 won discount\nGS Caltex",
            source_url="https://card-search.naver.com/card/b",
            confidence=Decimal("0.90"),
        )

        with (
            patch(
                "cards.management.commands.ingest_card_search_ai.scrape_card_search_candidates",
                return_value=[failing_candidate, saved_candidate],
            ),
            patch(
                "cards.management.commands.ingest_card_search_ai.normalize_card_fuel_benefit",
                side_effect=[
                    GeminiRequestError("temporary Gemini failure"),
                    _valid_llm_payload(CardPolicy.DiscountType.FIXED_AMOUNT, "10000"),
                ],
            ),
        ):
            call_command("ingest_card_search_ai", stdout=StringIO())

        self.assertEqual(CardCatalog.objects.count(), 1)
        self.assertEqual(CardCatalog.objects.get().card_name, "Card B")




def _candidate(raw_summary: str) -> ScrapedCardCandidate:
    return ScrapedCardCandidate(
        card_name="Card A",
        issuer_name="Issuer",
        discount_type=CardPolicy.DiscountType.PER_LITER,
        discount_value=Decimal("60"),
        raw_summary=raw_summary,
        source_url="https://card-search.naver.com/card/a",
        confidence=Decimal("0.90"),
    )


def _valid_llm_payload(discount_type: str, discount_value: str) -> dict:
    return {
        "card": {"name": "Card A", "issuer": "Issuer"},
        "fuel_sections": [
            {
                "section_title": "Fuel",
                "start_line": 2,
                "end_line": 4,
                "evidence_text": "Fuel\n60 won per liter discount\nGS Caltex"
                if discount_type == CardPolicy.DiscountType.PER_LITER
                else "Fuel\n10000 won discount\nGS Caltex",
                "reason": "Fuel benefit section",
            }
        ],
        "benefits": [
            {
                "category": "fuel",
                "fuel_type": "ALL",
                "discount_type": discount_type,
                "discount_value": discount_value,
                "brand_scope": "GS",
                "monthly_discount_limit": 10000,
                "evidence_section_index": 0,
                "evidence_text": "Fuel\n60 won per liter discount\nGS Caltex"
                if discount_type == CardPolicy.DiscountType.PER_LITER
                else "Fuel\n10000 won discount\nGS Caltex",
            }
        ],
        "quality": {"extraction_confidence": "0.9", "verification_status": "unverified", "warnings": []},
    }


def _contains_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(child, key) for child in value)
    return False
