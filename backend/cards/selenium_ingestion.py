import os
import re
import time
from dataclasses import dataclass, replace
from decimal import Decimal
from urllib.parse import urljoin, urlparse

from django.utils import timezone

from .models import CardCatalog, CardPolicy


DEFAULT_ALLOWED_DOMAINS = {"card-search.naver.com"}
DEFAULT_CARD_SEARCH_URL = (
    "https://card-search.naver.com/list?"
    "companyCode=&brandNames=&benefitCategoryIds=1&sortMethod=ri&isRefetch=true&bizType=CPC"
)


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


def normalize_candidate(candidate, source_url):
    name = " ".join((candidate.card_name or "").split())
    issuer = " ".join((candidate.issuer_name or "").split())
    if not name:
        return None

    return {
        "card_name": name[:120],
        "issuer_name": issuer[:120],
        "discount_type": candidate.discount_type,
        "discount_value": candidate.discount_value,
        "brand_scope": (candidate.brand_scope or "all")[:32],
        "min_payment_amount": candidate.min_payment_amount,
        "max_discount_amount": candidate.max_discount_amount,
        "monthly_discount_limit": candidate.monthly_discount_limit,
        "monthly_remaining_discount": candidate.monthly_remaining_discount,
        "card_image_url": candidate.card_image_url[:200] if candidate.card_image_url else "",
        "source_url": (candidate.source_url or source_url)[:200],
        "source_title": (candidate.source_title or name)[:255],
        "source_type": CardPolicy.SourceType.SELENIUM,
        "verification_status": CardPolicy.VerificationStatus.UNVERIFIED,
        "raw_summary": candidate.raw_summary[:2000],
        "confidence": candidate.confidence,
        "collected_at": timezone.now(),
    }


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
    confidence = min(Decimal("0.95"), base_confidence + (Decimal("0.04") * Decimal(found_fields)))
    if found_fields == 0:
        confidence = min(base_confidence, Decimal("0.60"))

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
        data = normalize_candidate(candidate, source_url)
        if not data:
            continue

        catalog_card = CardCatalog.objects.filter(source_url=data["source_url"]).first()
        if catalog_card is None:
            catalog_card = CardCatalog.objects.filter(
                card_name=data["card_name"],
                source_type=CardPolicy.SourceType.SELENIUM,
            ).first()

        if catalog_card is None:
            catalog_card = CardCatalog.objects.create(**data)
        else:
            for field_name, value in data.items():
                setattr(catalog_card, field_name, value)
            catalog_card.save()
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
        driver = webdriver.Chrome(options=options)
    except Exception as exc:
        raise CardIngestionError(
            "Unable to start Selenium Chrome. Ensure Chrome and ChromeDriver are available, "
            "or set CHROME_BINARY_PATH and allow Selenium Manager to resolve a driver."
        ) from exc
    try:
        driver.get(url)
        for _index in range(max(scroll_count, 0)):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        candidates = extract_candidates_from_dom(driver, url, limit=limit)
        if include_detail:
            return enrich_candidates_from_detail_pages(
                driver,
                candidates,
                wait_seconds=detail_wait_seconds,
            )
        return candidates
    finally:
        driver.quit()


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
