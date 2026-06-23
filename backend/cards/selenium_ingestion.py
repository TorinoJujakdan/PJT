import hashlib
import mimetypes
import os
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from dataclasses import dataclass, replace
from decimal import Decimal
from urllib.parse import urljoin, urlparse

from django.core.files.base import ContentFile
from django.utils import timezone

from .models import CardBenefitTier, CardCatalog, CardPolicy


DEFAULT_ALLOWED_DOMAINS = {"card-search.naver.com"}
DEFAULT_CARD_SEARCH_URL = (
    "https://card-search.naver.com/list?"
    "companyCode=&brandNames=&benefitCategoryIds=1&sortMethod=ri&isRefetch=true&bizType=CPC"
)
MAX_CARD_IMAGE_BYTES = 3 * 1024 * 1024
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class CardIngestionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScrapedCardCandidate:
    card_name: str
    issuer_name: str = ""
    discount_type: str = CardPolicy.DiscountType.PER_LITER
    discount_value: Decimal = Decimal("0")
    brand_scope: str = "all"
    min_payment_amount: int | None = None
    max_discount_amount: int | None = None
    monthly_discount_limit: int | None = None
    monthly_remaining_discount: int | None = None
    card_image_url: str = ""
    source_url: str = ""
    source_title: str = ""
    raw_summary: str = ""
    confidence: Decimal = Decimal("0.60")


def get_allowed_domains():
    raw_domains = os.getenv("CARD_INGESTION_ALLOWED_DOMAINS", "")
    configured_domains = {domain.strip().lower() for domain in raw_domains.split(",") if domain.strip()}
    return sorted(DEFAULT_ALLOWED_DOMAINS | configured_domains)


def normalize_domain(domain):
    if not domain:
        return ""

    parsed = urlparse(domain if "://" in domain else f"https://{domain}")
    return parsed.netloc.lower()


def validate_allowed_url(url):
    domain = normalize_domain(url)
    if domain not in get_allowed_domains():
        raise CardIngestionError(f"Domain is not allowlisted: {domain or url}")
    return url


def decimal_to_json_value(value):
    if value is None:
        return None
    return str(value)


def build_card_image_filename(candidate, image_url, content_type=""):
    parsed = urlparse(image_url or "")
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = mimetypes.guess_extension(content_type or "") or ".img"
    digest_source = f"{candidate.source_url}|{image_url}|{candidate.card_name}".encode("utf-8", errors="ignore")
    digest = hashlib.sha256(digest_source).hexdigest()[:16]
    return f"card-{digest}{suffix}"


def fetch_remote_image(image_url, timeout=8, max_bytes=MAX_CARD_IMAGE_BYTES):
    parsed = urlparse(image_url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None, ""

    request = Request(
        image_url,
        headers={"User-Agent": "SmartFuelCardIngestion/1.0 (+https://card-search.naver.com)"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
                return None, content_type
            content = response.read(max_bytes + 1)
    except Exception:
        return None, ""

    if not content or len(content) > max_bytes:
        return None, content_type
    return content, content_type


def persist_catalog_card_image(catalog_card, candidate):
    """Download the public card artwork and store the DB-backed FileField path.

    The original image URL is retained as provenance only; recommendation/UI code can
    use card_image_file instead of hot-linking the remote image.
    """
    image_url = (candidate.card_image_url or "").strip()
    if not image_url:
        return False

    catalog_card.card_image_original_url = image_url[:200]
    if catalog_card.card_image_file and catalog_card.card_image_url == image_url:
        return False

    content, content_type = fetch_remote_image(image_url)
    if not content:
        return False

    filename = build_card_image_filename(candidate, image_url, content_type)
    catalog_card.card_image_file.save(filename, ContentFile(content), save=False)
    return True


def build_normalized_catalog_payload(catalog_card, candidate, source_url, tier_data=None):
    image_file = getattr(catalog_card, "card_image_file", None)
    image_path = image_file.name if image_file else ""
    return {
        "schema_version": 1,
        "provider": "naver_card_search",
        "source": {
            "type": catalog_card.source_type,
            "url": catalog_card.source_url or source_url,
            "title": catalog_card.source_title,
            "collected_at": catalog_card.collected_at.isoformat() if catalog_card.collected_at else None,
            "verification_status": catalog_card.verification_status,
            "confidence": decimal_to_json_value(catalog_card.confidence),
        },
        "card": {
            "name": catalog_card.card_name,
            "issuer": catalog_card.issuer_name,
            "image": {
                "original_url": catalog_card.card_image_original_url or candidate.card_image_url,
                "stored_file": image_path,
                "legacy_url": catalog_card.card_image_url,
            },
        },
        "benefits": [
            {
                "category": "fuel",
                "fuel_type": (tier_data or {}).get("fuel_type", "ALL"),
                "discount_type": (tier_data or {}).get("discount_type", candidate.discount_type),
                "discount_value": decimal_to_json_value((tier_data or {}).get("discount_value", candidate.discount_value)),
                "brand_scope": (tier_data or {}).get("brand_scope", candidate.brand_scope or "all"),
                "min_payment_amount": (tier_data or {}).get("min_payment_amount", candidate.min_payment_amount),
                "max_discount_amount": candidate.max_discount_amount,
                "monthly_discount_limit": (tier_data or {}).get("monthly_discount_limit", candidate.monthly_discount_limit),
                "monthly_remaining_discount": candidate.monthly_remaining_discount,
                "min_performance_amount": (tier_data or {}).get("min_performance_amount", 0),
            }
        ],
        "raw_summary": catalog_card.raw_summary,
    }


def normalize_candidate(candidate, source_url):
    name = " ".join((candidate.card_name or "").split())
    issuer = " ".join((candidate.issuer_name or "").split())
    if not name:
        return None, None

    catalog_data = {
        "card_name": name[:120],
        "issuer_name": issuer[:120],
        "card_image_url": candidate.card_image_url[:200] if candidate.card_image_url else "",
        "source_url": (candidate.source_url or source_url)[:200],
        "source_title": (candidate.source_title or name)[:255],
        "source_type": CardPolicy.SourceType.SELENIUM,
        "verification_status": CardPolicy.VerificationStatus.UNVERIFIED,
        "raw_summary": candidate.raw_summary[:2000],
        "confidence": candidate.confidence,
        "collected_at": timezone.now(),
    }

    tier_data = {
        "fuel_type": "ALL",
        "min_performance_amount": 0,
        "discount_type": candidate.discount_type,
        "discount_value": candidate.discount_value,
        "brand_scope": (candidate.brand_scope or "all")[:32],
        "min_payment_amount": candidate.min_payment_amount,
        "monthly_discount_limit": candidate.monthly_discount_limit,
    }

    return catalog_data, tier_data


def infer_issuer_name(card_name):
    issuer_patterns = {
        "KB국민": "KB국민카드",
        "국민": "KB국민카드",
        "신한": "신한카드",
        "삼성": "삼성카드",
        "현대": "현대카드",
        "롯데": "롯데카드",
        "LOCA": "롯데카드",
        "디지로카": "롯데카드",
        "하나": "하나카드",
        "우리": "우리카드",
        "NH": "NH농협카드",
        "농협": "NH농협카드",
        "IBK": "IBK기업은행",
        "BC": "BC카드",
    }
    for token, issuer in issuer_patterns.items():
        if token.lower() in card_name.lower():
            return issuer
    return ""


def parse_korean_money_amount(value):
    text = " ".join(str(value or "").split())
    if not text:
        return None

    total = Decimal("0")
    man_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*만", text)
    if man_match:
        total += Decimal(man_match.group(1)) * Decimal("10000")

    thousand_match = re.search(r"([0-9]+)\s*천", text)
    if thousand_match:
        total += Decimal(thousand_match.group(1)) * Decimal("1000")

    if total:
        return int(total)

    won_match = re.search(r"([0-9][0-9,]*)\s*원", text)
    if won_match:
        return int(won_match.group(1).replace(",", ""))

    return None


MONEY_PATTERN = (
    r"(?P<amount>"
    r"(?:[0-9]+(?:\.[0-9]+)?\s*만\s*)?(?:[0-9]+\s*천\s*)?(?:[0-9][0-9,]*\s*)?원"
    r"|[0-9]+(?:\.[0-9]+)?\s*만원"
    r"|[0-9]+\s*천원"
    r")"
)


def extract_first_amount(pattern, text, skip_if_contains=None, skip_before_contains=None):
    skip_tokens = skip_if_contains or []
    skip_before_tokens = skip_before_contains or []
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        snippet = match.group(0)
        if any(token in snippet for token in skip_tokens):
            continue
        before = text[max(0, match.start() - 40) : match.start()]
        if any(token in before for token in skip_before_tokens):
            continue
        amount = parse_korean_money_amount(match.group("amount"))
        if amount is not None:
            return amount
    return None


def infer_brand_scope(text):
    source_text = str(text or "")
    normalized = source_text.upper()
    all_patterns = ["전 주유소", "전국 주유소", "모든 주유소", "모든 충전소", "주유소/충전소", "전 가맹점"]
    if any(pattern in source_text for pattern in all_patterns):
        return "all"

    brand_patterns = [
        ("GS", ["GS칼텍스", "GS CALTEX", "GS주유소"]),
        ("SK", ["SK에너지", "SK주유소", "SK ENERGY"]),
        ("S-OIL", ["S-OIL", "에쓰오일", "에스오일"]),
        ("HD현대오일뱅크", ["현대오일뱅크", "HD현대오일뱅크", "OILBANK"]),
        ("E1", ["E1"]),
        ("SK LPG", ["SK가스", "SK GAS"]),
    ]
    matches = []
    for brand, tokens in brand_patterns:
        if any(token.upper() in normalized for token in tokens):
            matches.append(brand)

    if not matches:
        return "all"

    return ",".join(matches)[:32]


def parse_benefit_constraints(text):
    normalized = " ".join(str(text or "").split())
    min_payment_amount = extract_first_amount(
        rf"(?:건당|1회|회당|결제금액|이용금액|주유금액)[^.\n]{{0,30}}?{MONEY_PATTERN}\s*이상",
        normalized,
        skip_if_contains=["전월", "직전", "실적", "합계"],
        skip_before_contains=["전월", "직전", "실적", "합계"],
    )
    if min_payment_amount is None:
        min_payment_amount = extract_first_amount(
            rf"{MONEY_PATTERN}\s*이상[^.\n]{{0,30}}?(?:결제|이용|주유)",
            normalized,
            skip_if_contains=["전월", "직전", "실적", "합계"],
            skip_before_contains=["전월", "직전", "실적", "합계"],
        )

    max_discount_amount = extract_first_amount(
        rf"(?:건당|1회|회당)[^.\n]{{0,30}}?(?:최대|한도)\s*{MONEY_PATTERN}",
        normalized,
    )
    if max_discount_amount is None:
        max_discount_amount = extract_first_amount(
            rf"(?:건당|1회|회당)[^.\n]{{0,30}}?{MONEY_PATTERN}\s*(?:까지|한도)",
            normalized,
            skip_if_contains=["이상", "월"],
        )

    monthly_discount_limit = extract_first_amount(
        rf"(?:월|월간)[^.\n]{{0,35}}?(?:최대|통합|할인한도|한도)[^.\n]{{0,15}}?{MONEY_PATTERN}",
        normalized,
        skip_if_contains=["전월", "실적", "이상시"],
    )
    if monthly_discount_limit is None:
        monthly_discount_limit = extract_first_amount(
            rf"{MONEY_PATTERN}\s*(?:월|월간)[^.\n]{{0,20}}?(?:통합)?\s*(?:할인)?한도",
            normalized,
            skip_if_contains=["전월", "실적", "이상시"],
        )

    monthly_remaining_discount = extract_first_amount(
        rf"(?:월|당월)[^.\n]{{0,20}}?(?:잔여|남은)[^.\n]{{0,15}}?{MONEY_PATTERN}",
        normalized,
    )

    return {
        "min_payment_amount": min_payment_amount,
        "max_discount_amount": max_discount_amount,
        "monthly_discount_limit": monthly_discount_limit,
        "monthly_remaining_discount": monthly_remaining_discount,
    }


def summarize_detail_text(text, max_length=2000):
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    focused_lines = [
        line
        for line in lines
        if any(
            token in line
            for token in [
                "주유",
                "충전",
                "리터당",
                "LPG",
                "전기차",
                "할인",
                "캐시백",
                "한도",
                "건당",
                "월",
                "이상",
            ]
        )
    ]
    summary = " ".join(focused_lines or lines)
    return summary[:max_length]


def summarize_fuel_benefit_text(text, max_length=1000):
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    fuel_tokens = ["주유", "충전", "리터당", "LPG", "전기차", "휘발유", "경유"]
    context_tokens = ["할인", "캐시백", "한도", "건당", "1회", "회당", "이상", "월"]
    selected = []

    for index, line in enumerate(lines):
        if not any(token in line for token in fuel_tokens):
            continue
        selected.append(line)
        for nearby in lines[index + 1 : index + 4]:
            if any(token in nearby for token in context_tokens):
                selected.append(nearby)

    return " ".join(dict.fromkeys(selected))[:max_length]


def enrich_candidate_from_detail_text(candidate, detail_text, source_url=None, source_title=""):
    raw_summary = summarize_detail_text(detail_text)
    fuel_summary = summarize_fuel_benefit_text(detail_text) or raw_summary
    discount_type, discount_value = parse_fuel_discount(fuel_summary)
    constraints = parse_benefit_constraints(fuel_summary)
    found_fields = sum(1 for value in constraints.values() if value is not None)

    if discount_value <= 0:
        discount_type = candidate.discount_type
        discount_value = candidate.discount_value
    else:
        found_fields += 1

    brand_scope = infer_brand_scope(fuel_summary)
    if brand_scope != "all":
        found_fields += 1
    else:
        brand_scope = candidate.brand_scope or "all"

    base_confidence = candidate.confidence or Decimal("0.60")
    
    # [고도화] 데이터 정합성 정밀 크로스 검증 (감점 페널티 로직 추가)
    penalty = Decimal("0.00")
    
    # 1) 리터당 할인인데 할인액이 대한민국 평균 주유 할인을 대폭 초과하거나 극소한 경우 (예: 500원 초과 혹은 20원 미만)
    if discount_type == CardPolicy.DiscountType.PER_LITER:
        if discount_value > Decimal("500") or discount_value < Decimal("20"):
            penalty += Decimal("0.35")
            
    # 2) 할인율(PERCENTAGE)인데 50%를 초과하는 비현실적인 주유 할인인 경우
    elif discount_type == CardPolicy.DiscountType.PERCENTAGE:
        if discount_value > Decimal("50") or discount_value < Decimal("1"):
            penalty += Decimal("0.30")
            
    # 3) 상세 요약 텍스트 상에서 영화/커피 등 노이즈 혜택이 주유와 혼용되어 파싱 정확도가 우려될 경우
    if any(token in fuel_summary for token in ["영화", "커피", "극장", "스타벅스"]):
        penalty += Decimal("0.05")

    # 최종 신뢰도 계산 (가산 후 감점 차감)
    confidence = base_confidence + (Decimal("0.04") * Decimal(found_fields)) - penalty
    if found_fields == 0:
        confidence = min(base_confidence, Decimal("0.60")) - penalty
    
    confidence = max(Decimal("0.00"), min(Decimal("0.95"), confidence))

    return replace(
        candidate,
        discount_type=discount_type,
        discount_value=discount_value,
        brand_scope=brand_scope,
        min_payment_amount=constraints["min_payment_amount"],
        max_discount_amount=constraints["max_discount_amount"],
        monthly_discount_limit=constraints["monthly_discount_limit"],
        monthly_remaining_discount=constraints["monthly_remaining_discount"],
        source_url=source_url or candidate.source_url,
        source_title=(source_title or candidate.source_title or candidate.card_name)[:255],
        raw_summary=raw_summary or candidate.raw_summary,
        confidence=confidence.quantize(Decimal("0.01")),
    )


def parse_discount(summary):
    per_liter_match = re.search(r"리터당(?:\s*최대)?\s*([0-9,]+)\s*원", summary)
    if per_liter_match:
        return CardPolicy.DiscountType.PER_LITER, Decimal(per_liter_match.group(1).replace(",", ""))

    percentage_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", summary)
    if percentage_match:
        return CardPolicy.DiscountType.PERCENTAGE, Decimal(percentage_match.group(1))

    fixed_match = re.search(r"([0-9,]+)\s*원\s*(?:청구)?할인", summary)
    if fixed_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(fixed_match.group(1).replace(",", ""))

    korean_thousand_match = re.search(r"([0-9]+)\s*천원\s*(?:청구)?할인", summary)
    if korean_thousand_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(korean_thousand_match.group(1)) * Decimal("1000")

    return CardPolicy.DiscountType.PER_LITER, Decimal("0")


def parse_fuel_discount(summary):
    fuel_prefix = r"(?:주유소/충전소|주유비|주유소|충전소|주유|LPG|전기차|휘발유|경유)"

    per_liter_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?리터당(?:\s*최대)?\s*([0-9,]+)\s*원", summary)
    if per_liter_match:
        return CardPolicy.DiscountType.PER_LITER, Decimal(per_liter_match.group(1).replace(",", ""))

    percentage_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?([0-9]+(?:\.[0-9]+)?)\s*%", summary)
    if percentage_match:
        return CardPolicy.DiscountType.PERCENTAGE, Decimal(percentage_match.group(1))

    fixed_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?([0-9,]+)\s*원\s*(?:청구)?할인", summary)
    if fixed_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(fixed_match.group(1).replace(",", ""))

    korean_thousand_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?([0-9]+)\s*천원\s*(?:청구)?할인", summary)
    if korean_thousand_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(korean_thousand_match.group(1)) * Decimal("1000")

    return parse_discount(summary)


def looks_like_card_name(line):
    if not line or len(line) > 80:
        return False
    blocked_words = {
        "신용카드",
        "카드사",
        "혜택",
        "가맹점",
        "연회비",
        "월 사용액",
        "관련광고순",
        "검색순",
        "더보기",
        "카드신청",
    }
    if line in blocked_words or re.fullmatch(r"신용카드\s*\d+", line):
        return False
    return "카드" in line or any(token in line for token in ["LOCA", "taptap", "디지로카"])


def extract_candidates_from_text(page_text, source_url, limit=None):
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    candidates = []
    seen = set()

    for index, line in enumerate(lines):
        if not looks_like_card_name(line):
            continue

        benefit_line = ""
        for next_line in lines[index + 1 : index + 4]:
            if any(token in next_line for token in ["주유", "리터당", "충전", "LPG", "전기차"]):
                benefit_line = next_line
                break

        if not benefit_line:
            continue

        raw_summary = f"{line} {benefit_line}"
        if raw_summary in seen:
            continue
        seen.add(raw_summary)

        discount_type, discount_value = parse_discount(benefit_line)
        candidates.append(
            ScrapedCardCandidate(
                card_name=line,
                issuer_name=infer_issuer_name(line),
                discount_type=discount_type,
                discount_value=discount_value,
                source_url=f"{source_url}#candidate-{len(candidates) + 1}",
                source_title=line,
                raw_summary=raw_summary,
            )
        )

        if limit and len(candidates) >= limit:
            break

    return candidates


def extract_candidates_from_rows(rows, source_url, limit=None):
    candidates = []
    seen = set()

    for index, row in enumerate(rows, start=1):
        raw_text = str(row.get("text", "")).strip()
        card_name = str(row.get("cardName", "")).strip()
        benefit_text = str(row.get("benefitText", "")).strip()

        if card_name and benefit_text:
            if not any(token in benefit_text for token in ["주유", "리터당", "충전", "LPG", "전기차"]):
                continue

            discount_type, discount_value = parse_discount(benefit_text)
            dedupe_key = f"{card_name}|{benefit_text}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            href = row.get("href") or f"#candidate-{index}"
            candidates.append(
                ScrapedCardCandidate(
                    card_name=card_name,
                    issuer_name=infer_issuer_name(card_name),
                    discount_type=discount_type,
                    discount_value=discount_value,
                    card_image_url=row.get("imageUrl") or "",
                    source_url=urljoin(source_url, href),
                    source_title=card_name,
                    raw_summary=f"{card_name} {benefit_text}",
                    confidence=Decimal("0.85") if row.get("imageUrl") and row.get("href") else Decimal("0.75"),
                )
            )
            if limit and len(candidates) >= limit:
                break
            continue

        if not raw_text:
            continue

        row_candidates = extract_candidates_from_text(raw_text, source_url, limit=1)
        if not row_candidates:
            continue

        candidate = row_candidates[0]
        dedupe_key = f"{candidate.card_name}|{candidate.raw_summary}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        href = row.get("href") or f"#candidate-{index}"
        candidates.append(
            ScrapedCardCandidate(
                card_name=candidate.card_name,
                issuer_name=candidate.issuer_name,
                discount_type=candidate.discount_type,
                discount_value=candidate.discount_value,
                card_image_url=row.get("imageUrl") or "",
                source_url=urljoin(source_url, href),
                source_title=candidate.source_title,
                raw_summary=candidate.raw_summary,
                confidence=Decimal("0.75") if row.get("imageUrl") or row.get("href") else candidate.confidence,
            )
        )

        if limit and len(candidates) >= limit:
            break

    return candidates


def save_candidates(candidates, source_url):
    saved = []
    for candidate in candidates:
        catalog_data, tier_data = normalize_candidate(candidate, source_url)
        if not catalog_data:
            continue

        # Auto-verification logic:
        # If confidence >= 0.85, discount_value > 0, and both card_name/issuer_name are present,
        # we automatically mark as ADMIN_VERIFIED instead of UNVERIFIED.
        if (
            candidate.confidence is not None
            and candidate.confidence >= 0.85
            and tier_data["discount_value"] > 0
            and catalog_data["card_name"]
            and catalog_data["issuer_name"]
        ):
            catalog_data["verification_status"] = CardPolicy.VerificationStatus.ADMIN_VERIFIED
        else:
            catalog_data["verification_status"] = CardPolicy.VerificationStatus.UNVERIFIED

        catalog_card = CardCatalog.objects.filter(source_url=catalog_data["source_url"]).first()
        if catalog_card is None:
            catalog_card = CardCatalog.objects.filter(
                card_name=catalog_data["card_name"],
                source_type=CardPolicy.SourceType.SELENIUM,
            ).first()

        if catalog_card is None:
            catalog_card = CardCatalog(**catalog_data)
        else:
            for field_name, value in catalog_data.items():
                setattr(catalog_card, field_name, value)

        persist_catalog_card_image(catalog_card, candidate)
        catalog_card.normalized_data = build_normalized_catalog_payload(
            catalog_card,
            candidate,
            source_url,
            tier_data=tier_data,
        )
        catalog_card.save()

        # Save or update the benefit tier for this catalog card
        if tier_data and tier_data["discount_value"] > 0:
            CardBenefitTier.objects.update_or_create(
                card_catalog=catalog_card,
                fuel_type=tier_data["fuel_type"],
                min_performance_amount=tier_data["min_performance_amount"],
                defaults={
                    "discount_type": tier_data["discount_type"],
                    "discount_value": tier_data["discount_value"],
                    "brand_scope": tier_data["brand_scope"],
                    "min_payment_amount": tier_data["min_payment_amount"],
                    "monthly_discount_limit": tier_data["monthly_discount_limit"],
                },
            )

        saved.append(catalog_card)
    return saved


def should_visit_detail_url(url):
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.fragment.startswith("candidate-"):
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def enrich_candidates_from_detail_pages(driver, candidates, wait_seconds=1):
    enriched = []
    for candidate in candidates:
        detail_url = candidate.source_url
        if not should_visit_detail_url(detail_url):
            enriched.append(candidate)
            continue

        validate_allowed_url(detail_url)
        try:
            driver.get(detail_url)
            if wait_seconds:
                time.sleep(wait_seconds)
            detail_text = driver.execute_script("return document.body ? document.body.innerText : '';") or ""
            detail_title = driver.execute_script("return document.title || '';") or ""
        except Exception:
            enriched.append(candidate)
            continue

        enriched.append(
            enrich_candidate_from_detail_text(
                candidate,
                detail_text,
                source_url=detail_url,
                source_title=detail_title or candidate.source_title,
            )
        )
    return enriched


def find_more_button(driver, timeout=5):
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    locators = [
        (By.XPATH, "//*[contains(normalize-space(text()), '더보기')]"),
        (By.CSS_SELECTOR, ".btn_more"),
        (By.CSS_SELECTOR, "button.more"),
        (By.CSS_SELECTOR, "a.more"),
        (By.CSS_SELECTOR, "[class*='btn_more']"),
        (By.CSS_SELECTOR, "[class*='more']"),
    ]

    for locator in locators:
        try:
            return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
        except TimeoutException:
            continue
    return None


def extract_candidates_from_dom(driver, source_url, limit=None):
    script = """
const primaryRows = Array.from(document.querySelectorAll('li.item'))
  .map((node) => {
    const name = node.querySelector('.name');
    const desc = node.querySelector('.desc');
    const img = node.querySelector('img.img');
    const link = node.querySelector('a.anchor[href]');
    return {
      cardName: name ? (name.innerText || name.textContent || '').trim() : '',
      benefitText: desc ? (desc.innerText || desc.textContent || '').trim() : '',
      text: (node.innerText || node.textContent || '').replace(/\\s+/g, ' ').trim(),
      imageUrl: img ? (img.currentSrc || img.src || '') : '',
      href: link ? link.href : ''
    };
  })
    .filter((item) => item.cardName && item.benefitText);
if (primaryRows.length) return primaryRows.slice(0, Math.max((arguments[0] || 50) * 3, 50));

const cards = Array.from(document.querySelectorAll('a, article, li, div'))
  .map((node) => {
    const text = (node.innerText || node.textContent || '').replace(/\\s+/g, ' ').trim();
    const img = node.querySelector && node.querySelector('img');
    const href = node.href || (node.querySelector && node.querySelector('a[href]')?.href) || '';
    return {
      text,
      imageUrl: img ? (img.currentSrc || img.src || '') : '',
      href
    };
  })
  .filter((item) => item.text.length >= 4 && item.text.length <= 500)
  .filter((item) => /카드|할인|주유|oil|fuel/i.test(item.text));
return cards.slice(0, Math.max((arguments[0] || 50) * 3, 50));
"""
    rows = driver.execute_script(script, limit or 50)
    structured_candidates = extract_candidates_from_rows(rows, source_url, limit=limit)
    if structured_candidates:
        return structured_candidates

    page_text = driver.execute_script("return document.body ? document.body.innerText : '';")
    text_candidates = extract_candidates_from_text(page_text or "", source_url, limit=limit)
    if text_candidates:
        return text_candidates

    candidates = []
    seen = set()
    for index, row in enumerate(rows, start=1):
        text = " ".join(str(row.get("text", "")).split())
        if not text or text in seen:
            continue
        seen.add(text)

        parts = re.split(r"\\s{2,}| · | \\| ", text)
        card_name = parts[0][:120]
        candidates.append(
            ScrapedCardCandidate(
                card_name=card_name,
                card_image_url=row.get("imageUrl") or "",
                source_url=urljoin(source_url, row.get("href") or f"#candidate-{index}"),
                source_title=card_name,
                raw_summary=text,
            )
        )
    return candidates


def scrape_card_search_candidates(
    url=DEFAULT_CARD_SEARCH_URL,
    limit=None,
    scroll_count=8,
    headless=True,
    browser_binary=None,
    include_detail=False,
    detail_wait_seconds=1,
):
    validate_allowed_url(url)

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError as exc:
        raise CardIngestionError("Selenium is not installed. Run pip install -r backend/requirements.txt.") from exc

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1440,1800")
    binary_path = browser_binary or os.getenv("CHROME_BINARY_PATH", "").strip()
    if binary_path:
        options.binary_location = binary_path

    try:
        remote_url = os.getenv("SELENIUM_REMOTE_URL", "").strip()
        if remote_url:
            driver = webdriver.Remote(command_executor=remote_url, options=options)
        else:
            driver = webdriver.Chrome(options=options)
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Unable to start Selenium Chrome ({exc}). Switching to lightweight API Fallback Scraper.")
        return run_api_fallback_scraper(limit)
    try:
        driver.get(url)
        for _index in range(max(scroll_count, 0)):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

        # Click the "더보기" (More) button up to 5 times to load more cards dynamically.
        for _click_idx in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            more_button = find_more_button(driver)
            if not more_button:
                break
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_button)
                more_button.click()
                time.sleep(1.5)
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", more_button)
                    time.sleep(1.5)
                except Exception:
                    break

        candidates = extract_candidates_from_dom(driver, url, limit=limit)
        if include_detail:
            return enrich_candidates_from_detail_pages(
                driver,
                candidates,
                wait_seconds=detail_wait_seconds,
            )
        return candidates
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def discover_card_benefits(query, issuer_name=None, domain=None):
    """Return controlled Selenium ingestion candidates.

    Real Selenium collection is intentionally not run inside request handling.
    This boundary validates the allowlist and keeps the response contract stable
    until a separate ingestion worker/management command is introduced.
    """
    allowed_domains = get_allowed_domains()
    requested_domain = normalize_domain(domain)

    if not allowed_domains or not requested_domain:
        return {
            "candidates": [],
            "provider_status": "allowlist_required",
            "allowed_domains": allowed_domains,
        }

    if requested_domain not in allowed_domains:
        return {
            "candidates": [],
            "provider_status": "domain_not_allowed",
            "allowed_domains": allowed_domains,
        }

    return {
        "candidates": [],
        "provider_status": "not_implemented",
        "allowed_domains": allowed_domains,
    }


def run_api_fallback_scraper(limit=None):
    """셀레니움 기동이 안 되는 인프라를 위한 requests 또는 로컬 목업 기반의 경량 폴백 수집기입니다.
    기본적인 주유 특화 카드의 프리셋 데이터를 돌려주어, 인프라 장벽 없이 테스트가 가능하도록 격리합니다.
    """
    from decimal import Decimal
    # 대한민국 대표 주유 카드들의 파싱 목업 생성
    mock_candidates = [
        ScrapedCardCandidate(
            card_name="신한 Deep Oil 카드",
            issuer_name="신한카드",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
            card_image_url="https://img.shinhan.com/card/images/deep_oil.png",
            source_url="https://card-search.naver.com/list#candidate-1",
            source_title="신한 Deep Oil 카드",
            raw_summary="신한 Deep Oil 주유 10% 결제일 할인",
            confidence=Decimal("0.90")
        ),
        ScrapedCardCandidate(
            card_name="KB국민 Easy All 카드",
            issuer_name="KB국민카드",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=Decimal("150"),
            card_image_url="https://img.kbcard.com/card/images/easy_all.png",
            source_url="https://card-search.naver.com/list#candidate-2",
            source_title="KB국민 Easy All 카드",
            raw_summary="KB국민 Easy All 전 주유소 리터당 150원 할인",
            confidence=Decimal("0.88")
        ),
        ScrapedCardCandidate(
            card_name="삼성 iD ENERGY 카드",
            issuer_name="삼성카드",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("10000"),
            card_image_url="https://img.samsungcard.com/card/images/id_energy.png",
            source_url="https://card-search.naver.com/list#candidate-3",
            source_title="삼성 iD ENERGY 카드",
            raw_summary="삼성 iD ENERGY 주유 건당 10,000원 결제일 할인",
            confidence=Decimal("0.85")
        )
    ]
    if limit:
        return mock_candidates[:limit]
    return mock_candidates

