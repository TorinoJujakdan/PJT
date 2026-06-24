from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from .models import CardBenefitTier, CardCatalog, CardPolicy
from .selenium_ingestion import (
    CardIngestionError,
    ScrapedCardCandidate,
    enrich_candidate_from_detail_text,
    extract_candidates_from_text,
    extract_candidates_from_rows,
    infer_brand_scope,
    infer_fuel_type,
    parse_benefit_constraints,
    parse_discount,
    parse_fuel_discount,
    save_candidates,
    validate_allowed_url,
)


class CardSeleniumIngestionTests(TestCase):
    def setUp(self):
        self._image_fetch_patch = patch("cards.selenium_ingestion.fetch_remote_image", return_value=(None, ""))
        self._image_fetch_patch.start()

    def tearDown(self):
        self._image_fetch_patch.stop()

    def test_validate_allowed_url_accepts_approved_naver_card_search_domain(self):
        url = "https://card-search.naver.com/list?benefitCategoryIds=1"

        self.assertEqual(validate_allowed_url(url), url)

    def test_validate_allowed_url_rejects_unknown_domain(self):
        with self.assertRaises(CardIngestionError):
            validate_allowed_url("https://example.com/cards")

    def test_save_candidates_creates_unverified_selenium_catalog_rows(self):
        source_url = "https://card-search.naver.com/list?benefitCategoryIds=1"
        candidates = [
            ScrapedCardCandidate(
                card_name="Smart Oil Card",
                issuer_name="Smart Bank",
                card_image_url="https://card-search.naver.com/card.png",
                source_url="https://card-search.naver.com/card/1",
                source_title="Smart Oil Card",
                raw_summary="Smart Oil Card 주유 할인",
                confidence=Decimal("0.50"),
            )
        ]

        saved = save_candidates(candidates, source_url=source_url)

        self.assertEqual(len(saved), 1)
        catalog = CardCatalog.objects.get()
        self.assertEqual(catalog.card_name, "Smart Oil Card")
        self.assertEqual(catalog.issuer_name, "Smart Bank")
        self.assertEqual(catalog.source_type, CardPolicy.SourceType.SELENIUM)
        self.assertEqual(catalog.verification_status, CardPolicy.VerificationStatus.UNVERIFIED)
        self.assertIsNotNone(catalog.collected_at)


    def test_save_candidates_downloads_card_image_and_stores_normalized_json(self):
        source_url = "https://card-search.naver.com/list?benefitCategoryIds=1"
        candidate = ScrapedCardCandidate(
            card_name="Smart Oil Card",
            issuer_name="Smart Bank",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=Decimal("80"),
            card_image_url="https://card-search.naver.com/card.png",
            source_url="https://card-search.naver.com/card/1",
            source_title="Smart Oil Card",
            raw_summary="Smart Oil Card fuel discount 80 KRW per liter",
            confidence=Decimal("0.80"),
        )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                with patch("cards.selenium_ingestion.fetch_remote_image", return_value=(b"fake-png", "image/png")):
                    save_candidates([candidate], source_url=source_url)

                catalog = CardCatalog.objects.get()
                self.assertEqual(catalog.card_image_original_url, "https://card-search.naver.com/card.png")
                self.assertTrue(catalog.card_image_file.name.startswith("card_images/catalog/card-"))
                self.assertEqual(catalog.normalized_data["schema_version"], 1)
                self.assertEqual(catalog.normalized_data["card"]["image"]["stored_file"], catalog.card_image_file.name)
                self.assertEqual(catalog.normalized_data["benefits"][0]["discount_value"], "80")

    def test_save_candidates_updates_existing_source_url(self):
        source_url = "https://card-search.naver.com/list?benefitCategoryIds=1"
        CardCatalog.objects.create(
            card_name="Old Name",
            source_url="https://card-search.naver.com/card/1",
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
            collected_at=timezone.now(),
        )

        save_candidates(
            [
                ScrapedCardCandidate(
                    card_name="New Name",
                    source_url="https://card-search.naver.com/card/1",
                )
            ],
            source_url=source_url,
        )

        self.assertEqual(CardCatalog.objects.count(), 1)
        self.assertEqual(CardCatalog.objects.get().card_name, "New Name")

    def test_save_candidates_updates_existing_card_name_when_source_url_changes(self):
        source_url = "https://card-search.naver.com/list?benefitCategoryIds=1"
        CardCatalog.objects.create(
            card_name="KB국민 굿데이카드",
            source_url="https://card-search.naver.com/list#candidate-1",
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )

        save_candidates(
            [
                ScrapedCardCandidate(
                    card_name="KB국민 굿데이카드",
                    source_url="https://card-search.naver.com/item?cardAdId=1",
                )
            ],
            source_url=source_url,
        )

        self.assertEqual(CardCatalog.objects.count(), 1)
        self.assertEqual(CardCatalog.objects.get().source_url, "https://card-search.naver.com/item?cardAdId=1")

    def test_parse_discount_supports_per_liter_and_percentage(self):
        self.assertEqual(parse_discount("주유소/충전소 리터당 60원 청구할인"), ("per_liter", Decimal("60")))
        self.assertEqual(parse_discount("주유 7% 할인"), ("percentage", Decimal("7")))
        self.assertEqual(parse_discount("주유비 최대 1.7% 캐시백"), ("percentage", Decimal("1.7")))
        self.assertEqual(parse_discount("주유소·LPG충전소 2천원 할인"), ("fixed_amount", Decimal("2000")))

    def test_parse_fuel_discount_ignores_non_fuel_cashback_percentage(self):
        discount_type, discount_value = parse_fuel_discount("온라인 신규회원 연회비 100% 캐시백")

        self.assertEqual(discount_type, CardPolicy.DiscountType.PER_LITER)
        self.assertEqual(discount_value, Decimal("0"))


    def test_parse_fuel_discount_catches_discount_before_fuel_keyword(self):
        self.assertEqual(
            parse_fuel_discount("리터당 80원 주유 할인"),
            (CardPolicy.DiscountType.PER_LITER, Decimal("80")),
        )
        self.assertEqual(
            parse_fuel_discount("7% 주유비 할인"),
            (CardPolicy.DiscountType.PERCENTAGE, Decimal("7")),
        )
        self.assertEqual(
            parse_fuel_discount("전월 실적 충족 시 80원/L 주유 할인"),
            (CardPolicy.DiscountType.PER_LITER, Decimal("80")),
        )

    def test_parse_fuel_discount_catches_bare_per_liter_amount_in_card_title(self):
        self.assertEqual(
            parse_fuel_discount("SK 주유 400 우리카드"),
            (CardPolicy.DiscountType.PER_LITER, Decimal("400")),
        )

    def test_extract_candidates_from_rows_prefers_fuel_percentage_over_cashback_percentage(self):
        rows = [
            {
                "cardName": "삼성 iD SELECT ALL 카드",
                "benefitText": "온라인신규회원 연회비 100% 캐시백 주유 7% 할인",
                "href": "/detail/select-all",
            }
        ]

        candidates = extract_candidates_from_rows(rows, "https://card-search.naver.com/list")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].discount_type, CardPolicy.DiscountType.PERCENTAGE)
        self.assertEqual(candidates[0].discount_value, Decimal("7"))

    def test_electric_vehicle_only_benefit_is_stored_as_ev_tier(self):
        rows = [
            {
                "cardName": "신한카드 EVerywhere",
                "benefitText": "전기차 충전요금 최대 50% 캐시백",
                "href": "/detail/everywhere",
            }
        ]

        candidates = extract_candidates_from_rows(rows, "https://card-search.naver.com/list")
        saved = save_candidates(candidates, "https://card-search.naver.com/list")

        self.assertEqual(len(saved), 1)
        tier = CardBenefitTier.objects.get(card_catalog=saved[0])
        self.assertEqual(tier.fuel_type, "EV")
        self.assertEqual(tier.discount_type, CardPolicy.DiscountType.PERCENTAGE)
        self.assertEqual(tier.discount_value, Decimal("50"))

    def test_infer_fuel_type_keeps_conventional_fuel_when_gasoline_evidence_exists(self):
        self.assertEqual(infer_fuel_type("전기차 충전요금 최대 50% 캐시백"), "EV")
        self.assertEqual(infer_fuel_type("주유소 리터당 80원 할인 전기차 충전요금 30% 할인"), "ALL")

    def test_extract_candidates_from_naver_card_search_text(self):
        page_text = """
신용카드 136
삼성 iD SIMPLE 카드
국내외가맹점 최대 1% 할인
국내 7천원, 해외 7천원
KB국민 굿데이카드
주유소/충전소 리터당 60원 청구할인
국내 5천원, 해외 1만원 주유 통신
삼성 iD SELECT ALL 카드
주유 7% 할인
국내 2만원, 해외 2만원
디지로카 London
주유비 최대 1.7% 캐시백
국내 2만원, 해외 2만원
"""

        candidates = extract_candidates_from_text(
            page_text,
            "https://card-search.naver.com/list?benefitCategoryIds=1",
        )

        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0].card_name, "KB국민 굿데이카드")
        self.assertEqual(candidates[0].issuer_name, "KB국민카드")
        self.assertEqual(candidates[0].discount_type, "per_liter")
        self.assertEqual(candidates[0].discount_value, Decimal("60"))
        self.assertEqual(candidates[1].discount_type, "percentage")
        self.assertEqual(candidates[1].discount_value, Decimal("7"))
        self.assertEqual(candidates[2].issuer_name, "롯데카드")
        self.assertEqual(candidates[2].discount_value, Decimal("1.7"))

    def test_extract_candidates_from_rows_keeps_image_and_detail_link(self):
        rows = [
            {
                "text": "KB국민 굿데이카드\n주유소/충전소 리터당 60원 청구할인",
                "cardName": "KB국민 굿데이카드",
                "benefitText": "주유소/충전소 리터당 60원 청구할인",
                "imageUrl": "https://card-search.naver.com/image.png",
                "href": "/detail/1",
            }
        ]

        candidates = extract_candidates_from_rows(rows, "https://card-search.naver.com/list")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].card_name, "KB국민 굿데이카드")
        self.assertEqual(candidates[0].card_image_url, "https://card-search.naver.com/image.png")
        self.assertEqual(candidates[0].source_url, "https://card-search.naver.com/detail/1")

    def test_infer_brand_scope_from_detail_text(self):
        self.assertEqual(infer_brand_scope("전국 모든 주유소 및 충전소 할인"), "all")
        self.assertEqual(infer_brand_scope("GS칼텍스, S-OIL 주유소 이용 시 할인"), "GS,S-OIL")
        self.assertEqual(infer_brand_scope("HD현대오일뱅크와 E1 충전소 혜택"), "HD현대오일뱅크,E1")

    def test_parse_benefit_constraints_from_detail_text(self):
        constraints = parse_benefit_constraints(
            "GS칼텍스 주유 할인은 건당 3만원 이상 결제 시 1회 최대 5천원 할인, "
            "월 통합 할인한도 2만원까지 제공됩니다."
        )

        self.assertEqual(constraints["min_payment_amount"], 30000)
        self.assertEqual(constraints["max_discount_amount"], 5000)
        self.assertEqual(constraints["monthly_discount_limit"], 20000)
        self.assertIsNone(constraints["monthly_remaining_discount"])

    def test_enrich_candidate_from_detail_text_parses_detail_fields(self):
        candidate = ScrapedCardCandidate(
            card_name="신한카드 Deep Oil",
            issuer_name="신한카드",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
            source_url="https://card-search.naver.com/detail/123",
            source_title="신한카드 Deep Oil",
            raw_summary="신한카드 Deep Oil 주유 10% 할인",
            confidence=Decimal("0.75"),
        )

        enriched = enrich_candidate_from_detail_text(
            candidate,
            """
            신한카드 Deep Oil
            GS칼텍스 주유 10% 할인
            건당 3만원 이상 결제 시 1회 최대 5천원 할인
            월 통합 할인한도 2만원
            """,
            source_title="신한카드 Deep Oil 상세",
        )

        self.assertEqual(enriched.brand_scope, "GS")
        self.assertEqual(enriched.min_payment_amount, 30000)
        self.assertEqual(enriched.max_discount_amount, 5000)
        self.assertEqual(enriched.monthly_discount_limit, 20000)
        self.assertEqual(enriched.source_title, "신한카드 Deep Oil 상세")
        self.assertGreater(enriched.confidence, Decimal("0.75"))

    def test_detail_enrichment_prefers_fuel_context_over_annual_fee_cashback(self):
        candidate = ScrapedCardCandidate(
            card_name="LOCA LIKIT 1.2",
            issuer_name="롯데카드",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=Decimal("1.20"),
            source_url="https://card-search.naver.com/item?cardAdId=10105",
            raw_summary="LOCA LIKIT 1.2 주유소 1.2% 결제일 할인",
            confidence=Decimal("0.85"),
        )

        enriched = enrich_candidate_from_detail_text(
            candidate,
            """
            신규 발급 100% 연회비 캐시백!
            국내외 가맹점 1.2% 할인
            주유
            주유소 1.2% 결제일 할인
            부가혜택 및 통합할인한도
            """,
        )

        self.assertEqual(enriched.discount_type, CardPolicy.DiscountType.PERCENTAGE)
        self.assertEqual(enriched.discount_value, Decimal("1.2"))

    def test_detail_enrichment_prefers_fuel_discount_when_line_has_other_percent(self):
        candidate = ScrapedCardCandidate(
            card_name="삼성 iD SELECT ALL 카드",
            issuer_name="삼성카드",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=Decimal("7"),
            source_url="https://card-search.naver.com/item?cardAdId=10522",
            raw_summary="삼성 iD SELECT ALL 카드 주유 7% 할인",
            confidence=Decimal("0.85"),
        )

        enriched = enrich_candidate_from_detail_text(
            candidate,
            """
            생활요금 할인 내게 맞춰 SELECT
            직전 1개월 합계 40만원 이상 아파트관리비 또는 교육 10% 할인,음식점/편의점/할인점/주유 7% 할인
            주유
            주유 7% 할인
            온라인신규회원 연회비 100% 캐시백
            """,
        )

        self.assertEqual(enriched.discount_type, CardPolicy.DiscountType.PERCENTAGE)
        self.assertEqual(enriched.discount_value, Decimal("7"))

    def test_detail_constraints_ignore_previous_month_spend_threshold(self):
        constraints = parse_benefit_constraints(
            "직전 1개월 합계 30만원 이상 교통·외식 등 생활영역 10% 청구할인 "
            "주유 주유소/충전소 리터당 60원 청구할인"
        )

        self.assertIsNone(constraints["min_payment_amount"])

    def test_detail_constraints_ignore_previous_month_spend_as_monthly_limit(self):
        constraints = parse_benefit_constraints(
            "전월실적50만원이상시 주유소 할인 주유 주유소·LPG충전소 2천원 할인 "
            "부가혜택 및 통합할인한도"
        )

        self.assertIsNone(constraints["monthly_discount_limit"])

    def test_save_detail_enrichment_updates_existing_catalog_row(self):
        detail_url = "https://card-search.naver.com/detail/123"
        CardCatalog.objects.create(
            card_name="신한카드 Deep Oil",
            issuer_name="신한카드",
            source_url=detail_url,
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.UNVERIFIED,
        )
        enriched = ScrapedCardCandidate(
            card_name="신한카드 Deep Oil",
            issuer_name="신한카드",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
            brand_scope="GS",
            min_payment_amount=30000,
            max_discount_amount=5000,
            monthly_discount_limit=20000,
            source_url=detail_url,
            source_title="신한카드 Deep Oil 상세",
            raw_summary="GS칼텍스 주유 10% 할인 건당 3만원 이상 월 통합 할인한도 2만원",
            confidence=Decimal("0.80"),
        )

        saved = save_candidates([enriched], source_url="https://card-search.naver.com/list")

        self.assertEqual(len(saved), 1)
        self.assertEqual(CardCatalog.objects.count(), 1)
        catalog = CardCatalog.objects.get()
        self.assertEqual(catalog.verification_status, CardPolicy.VerificationStatus.UNVERIFIED)
        # Tier에서 할인 정보 검증
        tier = CardBenefitTier.objects.get(card_catalog=catalog)
        self.assertEqual(tier.brand_scope, "GS")
        self.assertEqual(tier.discount_type, CardPolicy.DiscountType.PERCENTAGE)
        self.assertEqual(tier.discount_value, Decimal("10"))
        self.assertEqual(tier.min_payment_amount, 30000)
        self.assertEqual(tier.monthly_discount_limit, 20000)



class CardBenefitRepairCommandTests(TestCase):
    def test_repair_card_fuel_benefits_marks_ev_only_tier_as_ev(self):
        catalog = CardCatalog.objects.create(
            card_name="신한카드 EVerywhere",
            issuer_name="신한카드",
            source_url="https://card-search.naver.com/card/everywhere",
            raw_summary="전기차 충전요금 최대 50% 캐시백",
        )
        CardBenefitTier.objects.create(
            card_catalog=catalog,
            fuel_type="ALL",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=50,
        )
        output = StringIO()

        call_command("repair_card_fuel_benefits", stdout=output)

        tier = CardBenefitTier.objects.get(card_catalog=catalog)
        self.assertEqual(tier.fuel_type, "EV")
        self.assertIn("updated=1", output.getvalue())

    def test_repair_card_fuel_benefits_replaces_suspicious_tier_from_raw_summary(self):
        catalog = CardCatalog.objects.create(
            card_name="삼성 iD STATION 카드 (GS칼텍스)",
            issuer_name="삼성카드",
            source_url="https://card-search.naver.com/card/station-gs",
            raw_summary="GS칼텍스 주유 10% 할인 신규 회원 최대 100% 지급",
        )
        CardBenefitTier.objects.create(
            card_catalog=catalog,
            fuel_type="ALL",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=100,
        )
        output = StringIO()

        call_command("repair_card_fuel_benefits", stdout=output)

        tier = CardBenefitTier.objects.get(card_catalog=catalog)
        self.assertEqual(tier.discount_type, CardPolicy.DiscountType.PERCENTAGE)
        self.assertEqual(tier.discount_value, Decimal("10.00"))
        self.assertIn("updated=1", output.getvalue())

    def test_repair_card_fuel_benefits_creates_missing_tier_from_raw_summary(self):
        catalog = CardCatalog.objects.create(
            card_name="SK 주유 400 우리카드",
            issuer_name="우리카드",
            source_url="https://card-search.naver.com/card/sk-400",
            raw_summary="SK 주유 400 우리카드 SK 주유소 L당 청구할인",
        )
        output = StringIO()

        call_command("repair_card_fuel_benefits", stdout=output)

        tier = CardBenefitTier.objects.get(card_catalog=catalog)
        self.assertEqual(tier.discount_type, CardPolicy.DiscountType.PER_LITER)
        self.assertEqual(tier.discount_value, Decimal("400.00"))
        self.assertIn("created=1", output.getvalue())
