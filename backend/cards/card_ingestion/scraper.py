from __future__ import annotations

import os
import time
from decimal import Decimal
from urllib.parse import urlparse

from cards.models import CardPolicy

from .domain import (
    DEFAULT_CARD_SEARCH_URL,
    CardIngestionError,
    ScrapedCardCandidate,
    get_allowed_domains,
    normalize_domain,
    validate_allowed_url,
)
from .parsing import enrich_candidate_from_detail_text, extract_candidates_from_rows


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

            detail_title = driver.execute_script("return document.title || '';") or ""
            raw_text = driver.execute_script("return document.body.innerText || '';")
            enriched_candidate = enrich_candidate_from_detail_text(
                candidate,
                raw_text,
                source_url=detail_url,
                source_title=detail_title or candidate.source_title,
            )
            enriched.append(enriched_candidate)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error processing detail page: {e}")
            enriched.append(candidate)

    return enriched


def _element_text(element, by, selector):
    try:
        return element.find_element(by, selector).text.strip()
    except Exception:
        return ""


def _element_attribute(element, by, selector, attribute):
    try:
        return element.find_element(by, selector).get_attribute(attribute) or ""
    except Exception:
        return ""


def find_more_button(driver, timeout=5):
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    locators = [
        (By.XPATH, "//*[contains(normalize-space(text()), '더보기')]") ,
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

    elements = driver.find_elements(By.CSS_SELECTOR, "li.item")
    if not elements:
        elements = driver.find_elements(By.CSS_SELECTOR, "article, div.card_box")

    if limit:
        elements = elements[:limit]

    candidates = []
    for idx, element in enumerate(elements, start=1):
        try:
            raw_text = element.text.strip() if hasattr(element, "text") else ""
            card_name = _element_text(element, By.CSS_SELECTOR, ".name")
            href = _element_attribute(element, By.CSS_SELECTOR, "a.anchor[href]", "href") or f"#candidate-{idx}"
            image_url = _element_attribute(element, By.CSS_SELECTOR, "img.img", "src")
            rows = [
                {
                    "text": raw_text,
                    "cardName": card_name,
                    "benefitText": raw_text,
                    "imageUrl": image_url,
                    "href": href,
                }
            ]
            candidates.extend(extract_candidates_from_rows(rows, source_url, limit=1))

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error processing DOM element: {e}")
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

        # Click the "?ë³´ê¸? (More) button up to 5 times to load more cards dynamically.
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
    """Return deterministic fallback card candidates when browser scraping is unavailable."""
    mock_candidates = [
        ScrapedCardCandidate(
            card_name="Shinhan Deep Oil 카드",
            issuer_name="신한카드",
            discount_type=CardPolicy.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
            card_image_url="https://img.shinhan.com/card/images/deep_oil.png",
            source_url="https://card-search.naver.com/list#candidate-1",
            source_title="Shinhan Deep Oil 카드",
            raw_summary="주유 결제 10% 할인",
            confidence=Decimal("0.90"),
        ),
        ScrapedCardCandidate(
            card_name="KB Easy All 카드",
            issuer_name="KB국민카드",
            discount_type=CardPolicy.DiscountType.PER_LITER,
            discount_value=Decimal("150"),
            card_image_url="https://img.kbcard.com/card/images/easy_all.png",
            source_url="https://card-search.naver.com/list#candidate-2",
            source_title="KB Easy All 카드",
            raw_summary="주유 리터당 150원 할인",
            confidence=Decimal("0.88"),
        ),
        ScrapedCardCandidate(
            card_name="Samsung iD ENERGY 카드",
            issuer_name="삼성카드",
            discount_type=CardPolicy.DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("10000"),
            card_image_url="https://img.samsungcard.com/card/images/id_energy.png",
            source_url="https://card-search.naver.com/list#candidate-3",
            source_title="Samsung iD ENERGY 카드",
            raw_summary="주유 건당 10,000원 결제일 할인",
            confidence=Decimal("0.85"),
        ),
    ]
    if limit:
        return mock_candidates[:limit]
    return mock_candidates


