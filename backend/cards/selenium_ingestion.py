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
    fuel_type: str = "ALL"
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


def is_safe_url(url):
    import socket
    import ipaddress
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return False
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_multicast or ip_obj.is_unspecified:
                return False
        return True
    except (socket.gaierror, ValueError):
        return False

def fetch_remote_image(image_url, timeout=8, max_bytes=MAX_CARD_IMAGE_BYTES):
    parsed = urlparse(image_url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None, ""

    if not is_safe_url(image_url):
        return None, ""

    request = Request(
        image_url,
        headers={"User-Agent": "SmartFuelCardIngestion/1.0 (+https://card-search.naver.com)"},
    )
    try:
        import time
        import socket
        socket.setdefaulttimeout(timeout)
        with urlopen(request, timeout=timeout) as response:
            content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
                return None, content_type
            
            start_time = time.time()
            content = bytearray()
            while True:
                if time.time() - start_time > timeout:
                    return None, ""
                chunk = response.read(8192)
                if not chunk:
                    break
                content.extend(chunk)
                if len(content) > max_bytes:
                    break
            content = bytes(content)
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
        "KBêµ??": "KBêµ??ì¹´ë“œ",
        "êµ??": "KBêµ??ì¹´ë“œ",
        "? í•œ": "? í•œì¹´ë“œ",
        "?¼ì„±": "?¼ì„±ì¹´ë“œ",
        "?„ë?": "?„ë?ì¹´ë“œ",
        "ë¡?°": "ë¡?°ì¹´ë“œ",
        "LOCA": "ë¡?°ì¹´ë“œ",
        "?”ì?ë¡œì¹´": "ë¡?°ì¹´ë“œ",
        "?˜ë‚˜": "?˜ë‚˜ì¹´ë“œ",
        "?°ë¦¬": "?°ë¦¬ì¹´ë“œ",
        "NH": "NH?í˜‘ì¹´ë“œ",
        "?í˜‘": "NH?í˜‘ì¹´ë“œ",
        "IBK": "IBKê¸°ì—…?€??,
        "BC": "BCì¹´ë“œ",
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
    man_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*ë§?, text)
    if man_match:
        total += Decimal(man_match.group(1)) * Decimal("10000")

    thousand_match = re.search(r"([0-9]+)\s*ì²?, text)
    if thousand_match:
        total += Decimal(thousand_match.group(1)) * Decimal("1000")

    if total:
        return int(total)

    won_match = re.search(r"([0-9][0-9,]*)\s*??, text)
    if won_match:
        return int(won_match.group(1).replace(",", ""))

    return None


MONEY_PATTERN = (
    r"(?P<amount>"
    r"(?:[0-9]+(?:\.[0-9]+)?\s*ë§?s*)?(?:[0-9]+\s*ì²?s*)?(?:[0-9][0-9,]*\s*)???
    r"|[0-9]+(?:\.[0-9]+)?\s*ë§Œì›"
    r"|[0-9]+\s*ì²œì›"
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
    all_patterns = ["??ì£¼ìœ ??, "?„êµ­ ì£¼ìœ ??, "ëª¨ë“  ì£¼ìœ ??, "ëª¨ë“  ì¶©ì „??, "ì£¼ìœ ??ì¶©ì „??, "??ê°€ë§¹ì "]
    if any(pattern in source_text for pattern in all_patterns):
        return "all"

    brand_patterns = [
        ("GS", ["GSì¹¼í…??, "GS CALTEX", "GSì£¼ìœ ??]),
        ("SK", ["SK?ë„ˆì§€", "SKì£¼ìœ ??, "SK ENERGY"]),
        ("S-OIL", ["S-OIL", "?ì“°?¤ì¼", "?ìŠ¤?¤ì¼"]),
        ("HD?„ë??¤ì¼ë±…í¬", ["?„ë??¤ì¼ë±…í¬", "HD?„ë??¤ì¼ë±…í¬", "OILBANK"]),
        ("E1", ["E1"]),
        ("SK LPG", ["SKê°€??, "SK GAS"]),
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
        rf"(?:ê±´ë‹¹|1???Œë‹¹|ê²°ì œê¸ˆì•¡|?´ìš©ê¸ˆì•¡|ì£¼ìœ ê¸ˆì•¡)[^.\n]{{0,30}}?{MONEY_PATTERN}\s*?´ìƒ",
        normalized,
        skip_if_contains=["?„ì›”", "ì§ì „", "?¤ì ", "?©ê³„"],
        skip_before_contains=["?„ì›”", "ì§ì „", "?¤ì ", "?©ê³„"],
    )
    if min_payment_amount is None:
        min_payment_amount = extract_first_amount(
            rf"{MONEY_PATTERN}\s*?´ìƒ[^.\n]{{0,30}}?(?:ê²°ì œ|?´ìš©|ì£¼ìœ )",
            normalized,
            skip_if_contains=["?„ì›”", "ì§ì „", "?¤ì ", "?©ê³„"],
            skip_before_contains=["?„ì›”", "ì§ì „", "?¤ì ", "?©ê³„"],
        )

    max_discount_amount = extract_first_amount(
        rf"(?:ê±´ë‹¹|1???Œë‹¹)[^.\n]{{0,30}}?(?:ìµœë?|?œë„)\s*{MONEY_PATTERN}",
        normalized,
    )
    if max_discount_amount is None:
        max_discount_amount = extract_first_amount(
            rf"(?:ê±´ë‹¹|1???Œë‹¹)[^.\n]{{0,30}}?{MONEY_PATTERN}\s*(?:ê¹Œì?|?œë„)",
            normalized,
            skip_if_contains=["?´ìƒ", "??],
        )

    monthly_discount_limit = extract_first_amount(
        rf"(?:???”ê°„)[^.\n]{{0,35}}?(?:ìµœë?|?µí•©|? ì¸?œë„|?œë„)[^.\n]{{0,15}}?{MONEY_PATTERN}",
        normalized,
        skip_if_contains=["?„ì›”", "?¤ì ", "?´ìƒ??],
    )
    if monthly_discount_limit is None:
        monthly_discount_limit = extract_first_amount(
            rf"{MONEY_PATTERN}\s*(?:???”ê°„)[^.\n]{{0,20}}?(?:?µí•©)?\s*(?:? ì¸)??œë„",
            normalized,
            skip_if_contains=["?„ì›”", "?¤ì ", "?´ìƒ??],
        )

    monthly_remaining_discount = extract_first_amount(
        rf"(?:???¹ì›”)[^.\n]{{0,20}}?(?:?”ì—¬|?¨ì?)[^.\n]{{0,15}}?{MONEY_PATTERN}",
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
                "ì£¼ìœ ",
                "ì¶©ì „",
                "ë¦¬í„°??,
                "LPG",
                "?„ê¸°ì°?,
                "? ì¸",
                "ìºì‹œë°?,
                "?œë„",
                "ê±´ë‹¹",
                "??,
                "?´ìƒ",
            ]
        )
    ]
    summary = " ".join(focused_lines or lines)
    return summary[:max_length]


def summarize_fuel_benefit_text(text, max_length=1000):
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    fuel_tokens = ["ì£¼ìœ ", "ì¶©ì „", "ë¦¬í„°??, "LPG", "?„ê¸°ì°?, "?˜ë°œ??, "ê²½ìœ "]
    context_tokens = ["? ì¸", "ìºì‹œë°?, "?œë„", "ê±´ë‹¹", "1??, "?Œë‹¹", "?´ìƒ", "??]
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
    
    # [ê³ ë„?? ?°ì´???•í•©???•ë? ?¬ë¡œ??ê²€ì¦?
    penalty = Decimal("0.00")

    # 1) ë¦¬í„°??? ì¸?¸ë° ? ì¸?¡ì´ ë¹„í˜„?¤ì ??ê²½ìš° ??ê°??ì²´ë¥??ë³µ (hard block)
    if discount_type == CardPolicy.DiscountType.PER_LITER:
        if discount_value > Decimal("500") or discount_value < Decimal("20"):
            # ? ê·œ ?Œì› ?´ë²¤????ë¹„í˜„?¤ì  ê°?ì°¨ë‹¨ ???´ì „ candidate ê°’ìœ¼ë¡??˜ëŒë¦?
            discount_type = candidate.discount_type
            discount_value = candidate.discount_value
            penalty += Decimal("0.35")

    # 2) ? ì¸??PERCENTAGE)?¸ë° 50%ë¥?ì´ˆê³¼?˜ëŠ” ë¹„í˜„?¤ì  ? ì¸??ê²½ìš° ??hard block
    #    ?? "? ê·œ ?Œì› ìµœë? 100% ìºì‹œë°???ì£¼ìœ  ? ì¸?¼ë¡œ ?˜ëª» ?Œì‹±?˜ëŠ” ì¼€?´ìŠ¤ ë°©ì?
    elif discount_type == CardPolicy.DiscountType.PERCENTAGE:
        if discount_value > Decimal("50") or discount_value < Decimal("1"):
            discount_type = candidate.discount_type
            discount_value = candidate.discount_value
            penalty += Decimal("0.30")

    # 3) ?ì„¸ ?”ì•½ ?ìŠ¤???ì—???í™”/ì»¤í”¼ ???¸ì´ì¦??œíƒ??ì£¼ìœ ?€ ?¼ìš©??ê²½ìš°
    if any(token in fuel_summary for token in ["?í™”", "ì»¤í”¼", "ê·¹ì¥", "?¤í?ë²…ìŠ¤"]):
        penalty += Decimal("0.05")

    # ìµœì¢… ? ë¢°??ê³„ì‚° (ê°€????ê°ì  ì°¨ê°)
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
    per_liter_match = re.search(r"ë¦¬í„°???:\s*ìµœë?)?\s*([0-9,]+)\s*??, summary)
    if per_liter_match:
        return CardPolicy.DiscountType.PER_LITER, Decimal(per_liter_match.group(1).replace(",", ""))

    percentage_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", summary)
    if percentage_match:
        return CardPolicy.DiscountType.PERCENTAGE, Decimal(percentage_match.group(1))

    fixed_match = re.search(r"([0-9,]+)\s*??s*(?:ì²?µ¬)?? ì¸", summary)
    if fixed_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(fixed_match.group(1).replace(",", ""))

    korean_thousand_match = re.search(r"([0-9]+)\s*ì²œì›\s*(?:ì²?µ¬)?? ì¸", summary)
    if korean_thousand_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(korean_thousand_match.group(1)) * Decimal("1000")

    return CardPolicy.DiscountType.PER_LITER, Decimal("0")


def parse_fuel_discount(summary):
    fuel_prefix = r"(?:ì£¼ìœ ??ì¶©ì „??ì£¼ìœ ë¹?ì£¼ìœ ??ì¶©ì „??ì£¼ìœ |LPG|?„ê¸°ì°??˜ë°œ??ê²½ìœ )"

    per_liter_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?ë¦¬í„°???:\s*ìµœë?)?\s*([0-9,]+)\s*??, summary)
    if per_liter_match:
        return CardPolicy.DiscountType.PER_LITER, Decimal(per_liter_match.group(1).replace(",", ""))

    percentage_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?([0-9]+(?:\.[0-9]+)?)\s*%", summary)
    if percentage_match:
        return CardPolicy.DiscountType.PERCENTAGE, Decimal(percentage_match.group(1))

    fixed_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?([0-9,]+)\s*??s*(?:ì²?µ¬)?? ì¸", summary)
    if fixed_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(fixed_match.group(1).replace(",", ""))

    korean_thousand_match = re.search(rf"{fuel_prefix}[^.\n]{{0,50}}?([0-9]+)\s*ì²œì›\s*(?:ì²?µ¬)?? ì¸", summary)
    if korean_thousand_match:
        return CardPolicy.DiscountType.FIXED_AMOUNT, Decimal(korean_thousand_match.group(1)) * Decimal("1000")

    return parse_discount(summary)


def looks_like_card_name(line):
    if not line or len(line) > 80:
        return False
    blocked_words = {
        "? ìš©ì¹´ë“œ",
        "ì¹´ë“œ??,
        "?œíƒ",
        "ê°€ë§¹ì ",
        "?°íšŒë¹?,
        "???¬ìš©??,
        "ê´€?¨ê´‘ê³ ìˆœ",
        "ê²€?‰ìˆœ",
        "?”ë³´ê¸?,
        "ì¹´ë“œ? ì²­",
    }
    if line in blocked_words or re.fullmatch(r"? ìš©ì¹´ë“œ\s*\d+", line):
        return False
    return "ì¹´ë“œ" in line or any(token in line for token in ["LOCA", "taptap", "?”ì?ë¡œì¹´"])


def extract_candidates_from_text(page_text, source_url, limit=None):
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    candidates = []
    seen = set()

    for index, line in enumerate(lines):
        if not looks_like_card_name(line):
            continue

        benefit_line = ""
        for next_line in lines[index + 1 : index + 4]:
            if any(token in next_line for token in ["ì£¼ìœ ", "ë¦¬í„°??, "ì¶©ì „", "LPG", "?„ê¸°ì°?]):
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
            if not any(token in benefit_text for token in ["ì£¼ìœ ", "ë¦¬í„°??, "ì¶©ì „", "LPG", "?„ê¸°ì°?]):
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
    from selenium.webdriver.common.by import By
    from .gms_client import GMSClient
    
    gms = GMSClient.from_env()
    enriched = []
    
    for candidate in candidates:
        detail_url = candidate.source_url
        if not should_visit_detail_url(detail_url):
            enriched.append(candidate)
            continue

        validate_allowed_url(detail_url)
        
        from .models import CardCatalog, CardPolicy
        existing_card = CardCatalog.objects.filter(source_url=detail_url).first()
        if not existing_card and candidate.card_name:
            existing_card = CardCatalog.objects.filter(
                card_name=candidate.card_name,
                source_type=CardPolicy.SourceType.SELENIUM
            ).first()

        skip_vlm = False
        if existing_card:
            is_verified = (existing_card.verification_status == CardPolicy.VerificationStatus.ADMIN_VERIFIED)
            image_match = False
            if candidate.card_image_url:
                if existing_card.card_image_original_url == candidate.card_image_url or existing_card.card_image_url == candidate.card_image_url:
                    image_match = True
            
            if is_verified or image_match:
                skip_vlm = True
                if existing_card.raw_summary and len(existing_card.raw_summary) > 60:
                    skip_vlm = False
                else:
                    norm = existing_card.normalized_data or {}
                    benefits = norm.get("benefits", [])
                    if benefits:
                        b = benefits[0]
                        if b.get("min_payment_amount") is None and b.get("monthly_discount_limit") is None:
                            skip_vlm = False

        if skip_vlm:
            enriched.append(candidate)
            continue

        try:
            driver.get(detail_url)
            if wait_seconds:
                import time
                time.sleep(wait_seconds)
            
            detail_title = driver.execute_script("return document.title || '';") or ""
            png_bytes = driver.get_screenshot_as_png()
            import base64
            try:
                from PIL import Image
                from io import BytesIO
                with Image.open(BytesIO(png_bytes)) as img:
                    width, height = img.size
                    max_height = 2000
                    if height > max_height:
                        img = img.crop((0, 0, width, max_height))
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    base64_img = base64.b64encode(buffered.getvalue()).decode("utf-8")
            except ImportError:
                base64_img = base64.b64encode(png_bytes).decode("utf-8")
        except Exception:
            enriched.append(candidate)
            continue

        context = {
            "source_url": detail_url,
            "source_title": detail_title or candidate.source_title,
            "card_name": candidate.card_name,
            "issuer_name": candidate.issuer_name
        }

        try:
            payload = gms.normalize_multimodal(base64_img, context)
            card_info = payload.get("card") or {}
            benefits = payload.get("benefits") or []
            quality = payload.get("quality") or {}
            
            if not benefits:
                enriched.append(candidate)
                continue
                
            benefit = benefits[0]
            discount_val_str = str(benefit.get("discount_value") or 0)
            try:
                from decimal import Decimal
                discount_val = Decimal(discount_val_str)
            except Exception:
                from decimal import Decimal
                discount_val = Decimal("0")
            
            from .benefit_safety import is_usable_fuel_benefit
            discount_type = benefit.get("discount_type", candidate.discount_type)
            evidence_text = benefit.get("evidence_text", candidate.raw_summary)

            if not is_usable_fuel_benefit(discount_type, discount_val, evidence_text):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Discarding hallucinated VLM benefit on detail page: {discount_type} {discount_val} for {candidate.card_name}")
                enriched.append(candidate)
                continue
            
            from dataclasses import replace
            from decimal import Decimal
            enriched_candidate = replace(
                candidate,
                card_name=card_info.get("name") or candidate.card_name,
                issuer_name=card_info.get("issuer") or candidate.issuer_name,
                fuel_type=benefit.get("fuel_type", "ALL"),
                discount_type=discount_type,
                discount_value=discount_val if discount_val > 0 else candidate.discount_value,
                brand_scope=benefit.get("brand_scope", "all"),
                min_payment_amount=benefit.get("min_payment_amount", candidate.min_payment_amount),
                max_discount_amount=benefit.get("max_discount_amount", candidate.max_discount_amount),
                monthly_discount_limit=benefit.get("monthly_discount_limit", candidate.monthly_discount_limit),
                source_title=detail_title or candidate.source_title,
                raw_summary=evidence_text,
                confidence=Decimal(str(quality.get("extraction_confidence", "0.85")))
            )
            enriched.append(enriched_candidate)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error processing detail page for VLM: {e}")
            enriched.append(candidate)

    return enriched


def find_more_button(driver, timeout=5):
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    locators = [
        (By.XPATH, "//*[contains(normalize-space(text()), '?”ë³´ê¸?)]"),
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
    from selenium.webdriver.common.by import By
    from .gms_client import GMSClient

    gms = GMSClient.from_env()

    elements = driver.find_elements(By.CSS_SELECTOR, "li.item")
    if not elements:
        elements = driver.find_elements(By.CSS_SELECTOR, "article, div.card_box")

    if limit:
        elements = elements[:limit]

    candidates = []
    
    for idx, element in enumerate(elements, start=1):
        try:
            card_name = ""
            try:
                name_el = element.find_element(By.CSS_SELECTOR, ".name")
                card_name = name_el.text.strip()
            except Exception:
                pass
                
            href = ""
            try:
                link_el = element.find_element(By.CSS_SELECTOR, "a.anchor[href]")
                href = link_el.get_attribute("href")
            except Exception:
                pass
                
            image_url = ""
            try:
                img_el = element.find_element(By.CSS_SELECTOR, "img.img")
                image_url = img_el.get_attribute("src")
            except Exception:
                pass
                
            from urllib.parse import urljoin
            context = {
                "source_url": urljoin(source_url, href or f"#candidate-{idx}"),
                "source_title": card_name,
                "card_name": card_name,
                "issuer_name": ""
            }

            from .models import CardCatalog, CardPolicy
            from decimal import Decimal
            
            existing_card = CardCatalog.objects.filter(source_url=context["source_url"]).first()
            if not existing_card and card_name:
                existing_card = CardCatalog.objects.filter(
                    card_name=card_name,
                    source_type=CardPolicy.SourceType.SELENIUM
                ).first()

            skip_vlm = False
            if existing_card:
                is_verified = (existing_card.verification_status == CardPolicy.VerificationStatus.ADMIN_VERIFIED)
                image_match = False
                if image_url:
                    if existing_card.card_image_original_url == image_url or existing_card.card_image_url == image_url:
                        image_match = True
                
                if is_verified or image_match:
                    skip_vlm = True
                    if existing_card.raw_summary and len(existing_card.raw_summary) > 60:
                        skip_vlm = False
                    else:
                        norm = existing_card.normalized_data or {}
                        benefits = norm.get("benefits", [])
                        if benefits:
                            b = benefits[0]
                            if b.get("min_payment_amount") is None and b.get("monthly_discount_limit") is None:
                                skip_vlm = False

            if skip_vlm:
                norm_data = existing_card.normalized_data or {}
                card_info = norm_data.get("card", {})
                benefits = norm_data.get("benefits", [])
                benefit = benefits[0] if benefits else {}
                
                discount_val_str = str(benefit.get("discount_value") or 0)
                try:
                    discount_val = Decimal(discount_val_str)
                except Exception:
                    discount_val = Decimal("0")
                
                candidates.append(
                    ScrapedCardCandidate(
                        card_name=existing_card.card_name or card_name,
                        issuer_name=existing_card.issuer_name or "",
                        fuel_type=benefit.get("fuel_type", "ALL"),
                        discount_type=benefit.get("discount_type", CardPolicy.DiscountType.PER_LITER),
                        discount_value=discount_val,
                        brand_scope=benefit.get("brand_scope", "all"),
                        min_payment_amount=benefit.get("min_payment_amount"),
                        max_discount_amount=benefit.get("max_discount_amount"),
                        monthly_discount_limit=benefit.get("monthly_discount_limit"),
                        card_image_url=image_url or existing_card.card_image_original_url or existing_card.card_image_url,
                        source_url=context["source_url"],
                        source_title=context["source_title"],
                        raw_summary=existing_card.raw_summary or benefit.get("evidence_text", ""),
                        confidence=existing_card.confidence or Decimal("0.85")
                    )
                )
                continue

            base64_img = element.screenshot_as_base64
            
            payload = gms.normalize_multimodal(base64_img, context)
            card_info = payload.get("card") or {}
            benefits = payload.get("benefits") or []
            quality = payload.get("quality") or {}
            
            for benefit in benefits:
                discount_val_str = str(benefit.get("discount_value") or 0)
                try:
                    from decimal import Decimal
                    discount_val = Decimal(discount_val_str)
                except Exception:
                    from decimal import Decimal
                    discount_val = Decimal("0")
                
                discount_type = benefit.get("discount_type", CardPolicy.DiscountType.PER_LITER)
                evidence_text = benefit.get("evidence_text", "")

                from .benefit_safety import is_usable_fuel_benefit
                if not is_usable_fuel_benefit(discount_type, discount_val, evidence_text):
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Discarding hallucinated VLM benefit from DOM: {discount_type} {discount_val} for {card_info.get('name') or card_name}")
                    continue
                
                from decimal import Decimal
                from .models import CardPolicy
                candidates.append(
                    ScrapedCardCandidate(
                        card_name=card_info.get("name") or card_name,
                        issuer_name=card_info.get("issuer") or "",
                        fuel_type=benefit.get("fuel_type", "ALL"),
                        discount_type=discount_type,
                        discount_value=discount_val,
                        brand_scope=benefit.get("brand_scope", "all"),
                        min_payment_amount=benefit.get("min_payment_amount"),
                        max_discount_amount=benefit.get("max_discount_amount"),
                        monthly_discount_limit=benefit.get("monthly_discount_limit"),
                        card_image_url=image_url,
                        source_url=context["source_url"],
                        source_title=context["source_title"],
                        raw_summary=evidence_text,
                        confidence=Decimal(str(quality.get("extraction_confidence", "0.85")))
                    )
                )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error processing DOM element for VLM: {e}")
            continue

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

        # Click the "?”ë³´ê¸? (More) button up to 5 times to load more cards dynamically.
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
    """?€?ˆë‹ˆ?€ ê¸°ë™?????˜ëŠ” ?¸í”„?¼ë? ?„í•œ requests ?ëŠ” ë¡œì»¬ ëª©ì—… ê¸°ë°˜??ê²½ëŸ‰ ?´ë°± ?˜ì§‘ê¸°ì…?ˆë‹¤.
    ê¸°ë³¸?ì¸ ì£¼ìœ  ?¹í™” ì¹´ë“œ???„ë¦¬???°ì´?°ë? ?Œë ¤ì£¼ì–´, ?¸í”„???¥ë²½ ?†ì´ ?ŒìŠ¤?¸ê? ê°€?¥í•˜?„ë¡ ê²©ë¦¬?©ë‹ˆ??
    """
    from decimal import Decimal
    # ?€?œë?êµ??€??ì£¼ìœ  ì¹´ë“œ?¤ì˜ ?Œì‹± ëª©ì—… ?ì„±
    mock_candidates = [
        ScrapedCardCandidate(
            card_name="? í•œ Deep Oil ì¹´ë“œ",
            issuer_name="? í•œì¹´ë“œ",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
            card_image_url="https://img.shinhan.com/card/images/deep_oil.png",
            source_url="https://card-search.naver.com/list#candidate-1",
            source_title="? í•œ Deep Oil ì¹´ë“œ",
            raw_summary="? í•œ Deep Oil ì£¼ìœ  10% ê²°ì œ??? ì¸",
            confidence=Decimal("0.90")
        ),
        ScrapedCardCandidate(
            card_name="KBêµ?? Easy All ì¹´ë“œ",
            issuer_name="KBêµ??ì¹´ë“œ",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=Decimal("150"),
            card_image_url="https://img.kbcard.com/card/images/easy_all.png",
            source_url="https://card-search.naver.com/list#candidate-2",
            source_title="KBêµ?? Easy All ì¹´ë“œ",
            raw_summary="KBêµ?? Easy All ??ì£¼ìœ ??ë¦¬í„°??150??? ì¸",
            confidence=Decimal("0.88")
        ),
        ScrapedCardCandidate(
            card_name="?¼ì„± iD ENERGY ì¹´ë“œ",
            issuer_name="?¼ì„±ì¹´ë“œ",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("10000"),
            card_image_url="https://img.samsungcard.com/card/images/id_energy.png",
            source_url="https://card-search.naver.com/list#candidate-3",
            source_title="?¼ì„± iD ENERGY ì¹´ë“œ",
            raw_summary="?¼ì„± iD ENERGY ì£¼ìœ  ê±´ë‹¹ 10,000??ê²°ì œ??? ì¸",
            confidence=Decimal("0.85")
        )
    ]
    if limit:
        return mock_candidates[:limit]
    return mock_candidates

