from django.core.management.base import BaseCommand

from cards.benefit_safety import is_usable_fuel_benefit
from cards.models import CardBenefitTier, CardCatalog
from cards.selenium_ingestion import infer_fuel_type, parse_fuel_discount


class Command(BaseCommand):
    help = "Repair catalog fuel benefit tiers by reparsing raw fuel evidence and removing suspicious values."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report changes without writing them.")

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        created_count = 0
        updated_count = 0
        deleted_count = 0
        kept_count = 0

        catalogs = CardCatalog.objects.prefetch_related("benefit_tiers").all()
        for catalog in catalogs:
            raw_summary = catalog.raw_summary or ""
            parsed_type, parsed_value = parse_fuel_discount(raw_summary)
            parsed_fuel_type = infer_fuel_type(raw_summary)
            parsed_usable = is_usable_fuel_benefit(parsed_type, parsed_value, raw_summary)
            tiers = list(catalog.benefit_tiers.all())
            usable_tiers = [
                tier for tier in tiers if is_usable_fuel_benefit(tier.discount_type, tier.discount_value, raw_summary)
            ]

            if usable_tiers:
                for tier in usable_tiers:
                    if parsed_fuel_type == "EV" and tier.fuel_type != parsed_fuel_type:
                        if not dry_run:
                            tier.fuel_type = parsed_fuel_type
                            tier.save(update_fields=["fuel_type"])
                        updated_count += 1
                    else:
                        kept_count += 1
                suspicious_tiers = [tier for tier in tiers if tier not in usable_tiers]
                deleted_count += self._delete_tiers(suspicious_tiers, dry_run)
                continue

            if parsed_usable:
                if tiers:
                    tier = tiers[0]
                    if not dry_run:
                        tier.discount_type = parsed_type
                        tier.discount_value = parsed_value
                        if parsed_fuel_type == "EV":
                            tier.fuel_type = parsed_fuel_type
                        tier.brand_scope = tier.brand_scope or "all"
                        tier.save(update_fields=["discount_type", "discount_value", "fuel_type", "brand_scope"])
                        self._delete_tiers(tiers[1:], dry_run)
                    updated_count += 1
                    deleted_count += max(0, len(tiers) - 1)
                else:
                    if not dry_run:
                        CardBenefitTier.objects.create(
                            card_catalog=catalog,
                            fuel_type=parsed_fuel_type,
                            min_performance_amount=0,
                            discount_type=parsed_type,
                            discount_value=parsed_value,
                            brand_scope="all",
                        )
                    created_count += 1
                continue

            deleted_count += self._delete_tiers(tiers, dry_run)

        self.stdout.write(
            self.style.SUCCESS(
                "repair_card_fuel_benefits "
                f"created={created_count} updated={updated_count} deleted={deleted_count} kept={kept_count}"
            )
        )

    def _delete_tiers(self, tiers, dry_run):
        if not tiers:
            return 0
        tier_ids = [tier.id for tier in tiers]
        if not dry_run:
            CardBenefitTier.objects.filter(id__in=tier_ids).delete()
        return len(tier_ids)
