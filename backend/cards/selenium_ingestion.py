from __future__ import annotations

from .card_ingestion import images as _images
from .card_ingestion import persistence as _persistence
from .card_ingestion.domain import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    DEFAULT_ALLOWED_DOMAINS,
    DEFAULT_CARD_SEARCH_URL,
    MAX_CARD_IMAGE_BYTES,
    CardIngestionError,
    ScrapedCardCandidate,
    get_allowed_domains,
    normalize_domain,
    validate_allowed_url,
)
from .card_ingestion.images import (
    NoRedirectHandler,
    build_card_image_filename,
    is_safe_url,
)
from .card_ingestion.parsing import (
    MONEY_PATTERN,
    enrich_candidate_from_detail_text,
    extract_candidates_from_rows,
    extract_candidates_from_text,
    extract_first_amount,
    infer_brand_scope,
    infer_fuel_type,
    infer_issuer_name,
    looks_like_card_name,
    parse_benefit_constraints,
    parse_discount,
    parse_fuel_discount,
    parse_korean_money_amount,
    summarize_detail_text,
    summarize_fuel_benefit_text,
)
from .card_ingestion.persistence import (
    build_normalized_catalog_payload,
    decimal_to_json_value,
    normalize_candidate,
)
from .card_ingestion.scraper import (
    discover_card_benefits,
    enrich_candidates_from_detail_pages,
    extract_candidates_from_dom,
    find_more_button,
    run_api_fallback_scraper,
    scrape_card_search_candidates,
    should_visit_detail_url,
)


def fetch_remote_image(image_url, timeout=8, max_bytes=MAX_CARD_IMAGE_BYTES):
    return _images.fetch_remote_image(image_url, timeout=timeout, max_bytes=max_bytes)


def persist_catalog_card_image(catalog_card, candidate):
    return _images.persist_catalog_card_image(catalog_card, candidate, fetch_image=fetch_remote_image)


def save_candidates(candidates, source_url):
    return _persistence.save_candidates(candidates, source_url, persist_image=persist_catalog_card_image)
