from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from cards.ai_chunks import compute_raw_hash
from cards.ai_normalization import save_ai_normalized_candidates
from cards.gemini_client import (
    GeminiConfigurationError,
    GeminiRateLimitError,
    GeminiRequestError,
    normalize_card_fuel_benefit,
)
from cards.llm_fuel_extraction import build_line_numbered_document, validate_llm_fuel_payload
from cards.models import CardCatalog
from cards.selenium_ingestion import (
    DEFAULT_CARD_SEARCH_URL,
    CardIngestionError,
    scrape_card_search_candidates,
)


class Command(BaseCommand):
    help = "Ingest Naver card candidates through Gemini fuel-benefit normalization."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--url",
            default=DEFAULT_CARD_SEARCH_URL,
            help="Allowlisted Naver card search URL to collect.",
        )
        parser.add_argument("--limit", type=int, default=50, help="Maximum candidates to collect.")
        parser.add_argument("--scroll-count", type=int, default=8, help="Number of page-bottom scroll passes.")
        parser.add_argument(
            "--detail",
            action="store_true",
            help="Visit allowlisted detail URLs before normalization.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Normalize candidates without saving.")
        parser.add_argument("--headed", action="store_true", help="Run Chrome with a visible window.")
        parser.add_argument(
            "--browser-binary",
            default="",
            help="Optional Chrome executable path. Can also be set with CHROME_BINARY_PATH.",
        )
        parser.add_argument(
            "--normalizer",
            choices=["gemini"],
            default="gemini",
            help="Gemini API fuel-benefit extractor configured by GEMINI_* environment variables.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Save even when the same source_url and raw_hash already exist.",
        )

    def handle(self, *args, **options) -> None:
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

        saved_count = 0
        skipped_count = 0
        dry_run_count = 0
        failed_count = 0

        for candidate in candidates:
            raw_hash = compute_raw_hash(candidate.raw_summary)
            source_url = candidate.source_url
            if source_url and not options["force"] and self._same_raw_hash_exists(source_url, raw_hash):
                skipped_count += 1
                continue

            try:
                if options["dry_run"]:
                    payload = normalize_card_fuel_benefit(candidate)
                    validation = validate_llm_fuel_payload(
                        build_line_numbered_document(candidate.raw_summary),
                        payload,
                    )
                    quality = payload.get("quality")
                    confidence = (
                        quality.get("extraction_confidence", "unknown")
                        if isinstance(quality, dict)
                        else "unknown"
                    )
                    self.safe_write(
                        f"{candidate.card_name} | raw_hash={raw_hash} | "
                        f"confidence={confidence} | warnings={','.join(validation.warnings) or 'none'}"
                    )
                    dry_run_count += 1
                    continue

                saved = save_ai_normalized_candidates(
                    [candidate],
                    source_url=options["url"],
                    normalizer=normalize_card_fuel_benefit,
                )
                saved_count += len(saved)
            except (GeminiConfigurationError, GeminiRateLimitError, GeminiRequestError) as exc:
                failed_count += 1
                self.safe_write(self.style.WARNING(f"{candidate.card_name} | Gemini normalization failed: {exc}"))

        if failed_count and not saved_count and not dry_run_count:
            raise CommandError(f"Gemini normalization failed for all {failed_count} processed candidates.")

        if options["dry_run"]:
            self.safe_write(
                self.style.SUCCESS(
                    f"Normalized {dry_run_count} candidates without saving; "
                    f"skipped {skipped_count} unchanged; failed {failed_count}."
                )
            )
            return

        self.safe_write(
            self.style.SUCCESS(
                f"Saved {saved_count} Gemini-normalized candidates as unverified; "
                f"skipped {skipped_count} unchanged; failed {failed_count}."
            )
        )

    def _same_raw_hash_exists(self, source_url: str, raw_hash: str) -> bool:
        return CardCatalog.objects.filter(source_url=source_url, raw_hash=raw_hash).exists()

    def safe_write(self, message: str) -> None:
        safe_message = str(message).replace("\xa0", " ")
        self.stdout.write(safe_message.encode("cp949", errors="replace").decode("cp949"))
