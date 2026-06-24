from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlparse

from cards.models import CardPolicy



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


