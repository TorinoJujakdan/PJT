from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from cards.ai_normalization import save_ai_normalized_candidates
from cards.llm_fuel_extraction import build_line_numbered_document, validate_llm_fuel_payload
from cards.models import CardBenefitTier, CardCatalog, CardPolicy
from cards.selenium_ingestion import ScrapedCardCandidate
from stations.models import GasStation
from stations.services import calculate_card_discount


class LlmFuelExtractionTests(TestCase):
    def test_build_line_numbered_document_preserves_original_line_ranges(self):
        raw_text = "KB국민 마이핏카드\n주유\n최대 1만원 할인\nSK에너지·GS칼텍스"

        document = build_line_numbered_document(raw_text)

        self.assertEqual(
            document.numbered_text,
            "[001] KB국민 마이핏카드\n[002] 주유\n[003] 최대 1만원 할인\n[004] SK에너지·GS칼텍스",
        )
        self.assertEqual(document.section_text(2, 4), "주유\n최대 1만원 할인\nSK에너지·GS칼텍스")

    def test_validate_llm_payload_accepts_fuel_section_with_grounded_discount(self):
        raw_text = "KB국민 마이핏카드\n주유\n최대 1만원 할인\nSK에너지·GS칼텍스\n통신\n최대 1만원 할인"
        document = build_line_numbered_document(raw_text)
        payload = {
            "card": {"name": "KB국민 마이핏카드", "issuer": "KB국민카드"},
            "fuel_sections": [
                {
                    "section_title": "주유",
                    "start_line": 2,
                    "end_line": 4,
                    "evidence_text": "주유\n최대 1만원 할인\nSK에너지·GS칼텍스",
                    "reason": "주유 제목과 할인/브랜드 조건이 같은 블록임",
                }
            ],
            "benefits": [
                {
                    "category": "fuel",
                    "fuel_type": "ALL",
                    "discount_type": "fixed_amount",
                    "discount_value": "10000",
                    "brand_scope": "SK,GS",
                    "min_payment_amount": None,
                    "max_discount_amount": 10000,
                    "monthly_discount_limit": 10000,
                    "evidence_section_index": 0,
                    "evidence_text": "주유\n최대 1만원 할인\nSK에너지·GS칼텍스",
                }
            ],
            "quality": {"extraction_confidence": "0.86", "verification_status": "unverified", "warnings": []},
        }

        result = validate_llm_fuel_payload(document, payload)

        self.assertEqual(result.tier_data.discount_type, CardPolicy.DiscountType.FIXED_AMOUNT)
        self.assertEqual(result.tier_data.discount_value, Decimal("10000"))
        self.assertEqual(result.tier_data.brand_scope, "SK,GS")
        self.assertEqual(result.warnings, [])

    def test_validate_llm_payload_prefers_fuel_discount_over_general_merchant_discount(self):
        raw_text = "혜택\n국내외 가맹점 1% 할인\n주유\n리터당 60원 할인\n전 주유소"
        document = build_line_numbered_document(raw_text)
        payload = {
            "fuel_sections": [
                {
                    "section_title": "주유",
                    "start_line": 3,
                    "end_line": 5,
                    "evidence_text": "주유\n리터당 60원 할인\n전 주유소",
                    "reason": "주유 제목 아래 할인 조건",
                }
            ],
            "benefits": [
                {
                    "category": "fuel",
                    "fuel_type": "ALL",
                    "discount_type": "per_liter",
                    "discount_value": "60",
                    "brand_scope": "all",
                    "evidence_section_index": 0,
                    "evidence_text": "주유\n리터당 60원 할인\n전 주유소",
                }
            ],
        }

        result = validate_llm_fuel_payload(document, payload)

        self.assertEqual(result.tier_data.discount_type, CardPolicy.DiscountType.PER_LITER)
        self.assertEqual(result.tier_data.discount_value, Decimal("60"))

    def test_validate_llm_payload_rejects_ungrounded_discount(self):
        raw_text = "주유\n리터당 60원 할인\n전 주유소"
        document = build_line_numbered_document(raw_text)
        payload = {
            "fuel_sections": [
                {
                    "section_title": "주유",
                    "start_line": 1,
                    "end_line": 3,
                    "evidence_text": "주유\n리터당 60원 할인\n전 주유소",
                    "reason": "주유 블록",
                }
            ],
            "benefits": [
                {
                    "category": "fuel",
                    "fuel_type": "ALL",
                    "discount_type": "per_liter",
                    "discount_value": "200",
                    "brand_scope": "all",
                    "evidence_section_index": 0,
                    "evidence_text": "주유\n리터당 60원 할인\n전 주유소",
                }
            ],
        }

        result = validate_llm_fuel_payload(document, payload)

        self.assertIsNone(result.tier_data)
        self.assertIn("discount_value_not_supported_by_evidence", result.warnings)


class AiNormalizedCandidateSaveTests(TestCase):
    def setUp(self):
        self._image_fetch_patch = __import__("unittest.mock").mock.patch(
            "cards.selenium_ingestion.fetch_remote_image",
            return_value=(None, ""),
        )
        self._image_fetch_patch.start()

    def tearDown(self):
        self._image_fetch_patch.stop()

    def test_save_ai_normalized_candidates_stores_valid_llm_tier_for_recommendations(self):
        source_url = "https://card-search.naver.com/list?benefitCategoryIds=1"
        raw_text = "KB국민 마이핏카드\n주유\n최대 1만원 할인\nSK에너지·GS칼텍스"
        candidate = ScrapedCardCandidate(
            card_name="KB국민 마이핏카드",
            issuer_name="KB국민카드",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=Decimal("1"),
            raw_summary=raw_text,
            source_url="https://card-search.naver.com/card/llm-1",
        )
        llm_payload = {
            "fuel_sections": [
                {
                    "section_title": "주유",
                    "start_line": 2,
                    "end_line": 4,
                    "evidence_text": "주유\n최대 1만원 할인\nSK에너지·GS칼텍스",
                    "reason": "주유 블록",
                }
            ],
            "benefits": [
                {
                    "category": "fuel",
                    "fuel_type": "ALL",
                    "discount_type": "fixed_amount",
                    "discount_value": "10000",
                    "brand_scope": "SK,GS",
                    "monthly_discount_limit": 10000,
                    "evidence_section_index": 0,
                    "evidence_text": "주유\n최대 1만원 할인\nSK에너지·GS칼텍스",
                }
            ],
        }

        saved = save_ai_normalized_candidates(
            [candidate],
            source_url=source_url,
            normalizer=lambda _candidate: llm_payload,
        )

        self.assertEqual(len(saved), 1)
        catalog = CardCatalog.objects.get()
        tier = CardBenefitTier.objects.get(card_catalog=catalog)
        self.assertEqual(tier.discount_type, CardPolicy.DiscountType.FIXED_AMOUNT)
        self.assertEqual(tier.discount_value, Decimal("10000.00"))
        self.assertEqual(catalog.normalized_data["benefits"][0]["discount_value"], "10000")
        self.assertEqual(catalog.normalized_data["quality"]["warnings"], [])

        user = get_user_model().objects.create_user(username="llm-card-user", password="pass12345")
        policy = CardPolicy.objects.create(
            owner=user,
            linked_catalog=catalog,
            card_name=catalog.card_name,
            issuer_name=catalog.issuer_name,
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=Decimal("1"),
            previous_month_spending=0,
            source_type=CardPolicy.SourceType.CATALOG,
        )
        station = GasStation.objects.create(
            name="GS 테스트",
            brand="GS",
            address="서울시",
            latitude=37.5,
            longitude=127.0,
        )
        recommendation_candidate = type(
            "StationCandidate",
            (),
            {"fuel_type": "GASOLINE", "station": station},
        )()

        discount, selected_card = calculate_card_discount(
            recommendation_candidate,
            refuel_cost=50000,
            target_liters=30,
            user_cards=[policy],
        )

        self.assertEqual(discount, 10000)
        self.assertEqual(selected_card["discount_type"], CardPolicy.DiscountType.FIXED_AMOUNT)
