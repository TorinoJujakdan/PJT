from django.core.management.base import BaseCommand, CommandError

from cards.selenium_ingestion import (
    DEFAULT_CARD_SEARCH_URL,
    CardIngestionError,
    save_candidates,
    scrape_card_search_candidates,
)


class Command(BaseCommand):
    help = "Ingest public card benefit candidates from an allowlisted Selenium source."

    def safe_write(self, message):
        safe_message = str(message).replace("\xa0", " ")
        self.stdout.write(safe_message.encode("cp949", errors="replace").decode("cp949"))

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            default=DEFAULT_CARD_SEARCH_URL,
            help="Allowlisted card search URL to collect. Defaults to the approved Naver card search source.",
        )
        parser.add_argument("--limit", type=int, default=50, help="Maximum candidates to collect.")
        parser.add_argument("--scroll-count", type=int, default=8, help="Number of page-bottom scroll passes.")
        parser.add_argument(
            "--detail",
            action="store_true",
            help="Visit allowlisted candidate detail URLs and enrich CardCatalog fields.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Collect and print candidates without saving.")
        parser.add_argument("--headed", action="store_true", help="Run Chrome with a visible window.")
        parser.add_argument(
            "--browser-binary",
            default="",
            help="Optional Chrome executable path. Can also be set with CHROME_BINARY_PATH.",
        )

    def handle(self, *args, **options):
        try:
            candidates = scrape_card_search_candidates(
                url=options["url"],
                limit=options["limit"],
                scroll_count=options["scroll_count"],
                headless=not options["headed"],
                browser_binary=options["browser_binary"] or None,
                include_detail=options["detail"],
            )
        except CardIngestionError as exc:
            raise CommandError(str(exc)) from exc

        if options["dry_run"]:
            for candidate in candidates:
                self.safe_write(
                    f"{candidate.card_name} | {candidate.discount_type} {candidate.discount_value} | "
                    f"brand={candidate.brand_scope} | min={candidate.min_payment_amount} | "
                    f"max={candidate.max_discount_amount} | monthly={candidate.monthly_discount_limit} | "
                    f"confidence={candidate.confidence} | {candidate.raw_summary} | {candidate.source_url}"
                )
            self.safe_write(self.style.SUCCESS(f"Collected {len(candidates)} candidates without saving."))
            return

        saved = save_candidates(candidates, source_url=options["url"])
        self.stdout.write(self.style.SUCCESS(f"Saved {len(saved)} unverified card catalog candidates."))
