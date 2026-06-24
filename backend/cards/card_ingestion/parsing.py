from __future__ import annotations

from .benefits import (
    enrich_candidate_from_detail_text,
    infer_brand_scope,
    infer_fuel_type,
    parse_benefit_constraints,
    parse_discount,
    parse_fuel_discount,
    summarize_detail_text,
    summarize_fuel_benefit_text,
)
from .candidate_extraction import (
    extract_candidates_from_rows,
    extract_candidates_from_text,
    infer_issuer_name,
    looks_like_card_name,
)
from .money import MONEY_PATTERN, extract_first_amount, parse_korean_money_amount
