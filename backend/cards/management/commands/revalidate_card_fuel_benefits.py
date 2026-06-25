from __future__ import annotations

from django.core.management.base import BaseCommand

from cards.benefit_safety import has_fuel_context, is_usable_fuel_benefit
from cards.models import CardBenefitTier, CardCatalog
from cards.selenium_ingestion import infer_fuel_type, parse_fuel_discount


class Command(BaseCommand):
    help = "Revalidate catalog fuel benefits, write audit status, and clear unsafe stale tiers."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Report changes without writing them.")

    def handle(self, *args, **options) -> None:
        dry_run = bool(options["dry_run"])
        counts = {
            "verified": 0,
            "held_relevance_missing": 0,
            "skipped_insufficient_source": 0,
            "unknown": 0,
            "errors": 0,
            "deleted_tiers": 0,
        }
        for catalog in CardCatalog.objects.prefetch_related("benefit_tiers").all():
            try:
                fuel_status = self._status_for(catalog)
                counts[fuel_status] += 1
                if fuel_status == "verified":
                    self._ensure_verified_tier(catalog, dry_run)
                else:
                    counts["deleted_tiers"] += self._delete_tiers(catalog, dry_run)
                self._write_status(catalog, fuel_status, dry_run)
            except Exception as exc:
                counts["errors"] += 1
                self.stderr.write(f"catalog_id={catalog.id} error={exc}")

        self.stdout.write(
            self.style.SUCCESS(
                "revalidate_card_fuel_benefits "
                + " ".join(f"{key}={value}" for key, value in counts.items())
            )
        )

    def _status_for(self, catalog: CardCatalog) -> str:
        raw_summary = (catalog.raw_summary or "").strip()
        if not raw_summary:
            return "skipped_insufficient_source"
        discount_type, discount_value = parse_fuel_discount(raw_summary)
        if is_usable_fuel_benefit(discount_type, discount_value, raw_summary):
            return "verified"
        if not has_fuel_context(raw_summary):
            return "held_relevance_missing"
        return "skipped_insufficient_source"

    def _ensure_verified_tier(self, catalog: CardCatalog, dry_run: bool) -> None:
        if dry_run:
            return
        raw_summary = catalog.raw_summary or ""
        discount_type, discount_value = parse_fuel_discount(raw_summary)
        fuel_type = infer_fuel_type(raw_summary)
        tiers = list(catalog.benefit_tiers.all())
        if tiers:
            tier = tiers[0]
            tier.discount_type = discount_type
            tier.discount_value = discount_value
            tier.fuel_type = fuel_type
            tier.brand_scope = tier.brand_scope or "all"
            tier.save(update_fields=["discount_type", "discount_value", "fuel_type", "brand_scope"])
            extra_ids = [extra.id for extra in tiers[1:]]
            if extra_ids:
                CardBenefitTier.objects.filter(id__in=extra_ids).delete()
            return
        CardBenefitTier.objects.create(
            card_catalog=catalog,
            fuel_type=fuel_type,
            min_performance_amount=0,
            discount_type=discount_type,
            discount_value=discount_value,
            brand_scope="all",
        )

    def _delete_tiers(self, catalog: CardCatalog, dry_run: bool) -> int:
        tier_ids = [tier.id for tier in catalog.benefit_tiers.all()]
        if tier_ids and not dry_run:
            CardBenefitTier.objects.filter(id__in=tier_ids).delete()
        return len(tier_ids)

    def _write_status(self, catalog: CardCatalog, fuel_status: str, dry_run: bool) -> None:
        if dry_run:
            return
        normalized_data = dict(catalog.normalized_data or {})
        quality = dict(normalized_data.get("quality") or {})
        warnings = list(quality.get("warnings") or [])
        marker = _warning_for_status(fuel_status)
        if marker and marker not in warnings:
            warnings.append(marker)
        quality["warnings"] = warnings
        quality["fuel_benefit_status"] = fuel_status
        normalized_data["quality"] = quality
        catalog.normalized_data = normalized_data
        catalog.save(update_fields=["normalized_data"])


def _warning_for_status(fuel_status: str) -> str:
    if fuel_status == "held_relevance_missing":
        return "fuel_benefit_relevance_missing"
    if fuel_status == "skipped_insufficient_source":
        return "fuel_benefit_insufficient_source"
    return ""
