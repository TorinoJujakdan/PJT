from __future__ import annotations

import re
from decimal import Decimal
from urllib.parse import urljoin

from .benefits import parse_fuel_discount
from .domain import ScrapedCardCandidate


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
        "IBK": "IBK기업은행카드",
        "BC": "BC카드",
    }
    for token, issuer in issuer_patterns.items():
        if token.lower() in card_name.lower():
            return issuer
    return ""


def looks_like_card_name(line):
    if not line or len(line) > 80:
        return False
    blocked_words = {
        "신용카드",
        "카드사",
        "혜택",
        "가맹점",
        "조회비",
        "사용처",
        "관심광고순",
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
            if any(token in next_line for token in ["주유", "리터", "충전", "LPG", "전기차"]):
                benefit_line = next_line
                break

        if not benefit_line:
            continue

        raw_summary = f"{line} {benefit_line}"
        if raw_summary in seen:
            continue
        seen.add(raw_summary)

        discount_type, discount_value = parse_fuel_discount(benefit_line)
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
            if not any(token in benefit_text for token in ["주유", "리터", "충전", "LPG", "전기차"]):
                continue

            discount_type, discount_value = parse_fuel_discount(benefit_text)
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


