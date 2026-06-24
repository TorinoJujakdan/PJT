from __future__ import annotations

from django.utils import timezone

from cards.models import CardBenefitTier, CardCatalog, CardPolicy

from .parsing import infer_fuel_type


def _default_persist_catalog_card_image(catalog_card, candidate):
    from cards import selenium_ingestion as ingestion_api

    return ingestion_api.persist_catalog_card_image(catalog_card, candidate)

def decimal_to_json_value(value):
    if value is None:
        return None
    return str(value)


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

    fuel_type = candidate.fuel_type or "ALL"
    if fuel_type == "ALL":
        fuel_type = infer_fuel_type(candidate.raw_summary)

    tier_data = {
        "fuel_type": fuel_type,
        "min_performance_amount": 0,
        "discount_type": candidate.discount_type,
        "discount_value": candidate.discount_value,
        "brand_scope": (candidate.brand_scope or "all")[:32],
        "min_payment_amount": candidate.min_payment_amount,
        "monthly_discount_limit": candidate.monthly_discount_limit,
    }

    return catalog_data, tier_data


def save_candidates(candidates, source_url, persist_image=None):
    saved = []
    for candidate in candidates:
        catalog_data, tier_data = normalize_candidate(candidate, source_url)
        if not catalog_data:
            continue
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

        (persist_image or _default_persist_catalog_card_image)(catalog_card, candidate)
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


