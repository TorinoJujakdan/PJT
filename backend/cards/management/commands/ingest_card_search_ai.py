from django.core.management.base import BaseCommand, CommandError

from cards.ai_normalization import (
    RawCardDocument,
    build_card_raw_text,
    compute_raw_hash,
    normalize_raw_document,
    save_ai_normalized_candidate,
)
from cards.gms_client import GMSClient, GMSConfigurationError, GMSRequestError, GMSResponseFormatError
from cards.models import CardCatalog
from cards.selenium_ingestion import (
    DEFAULT_CARD_SEARCH_URL,
    CardIngestionError,
    scrape_card_search_candidates,
)


class Command(BaseCommand):
    help = "Ingest Naver card candidates through chunked AI normalization with default unverified storage."

    def add_arguments(self, parser):
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
            "--model-name",
            default="chunked-llm-ready-v1",
            help="Local model label. GMS mode uses GMS_MODEL from backend/.env.",
        )
        parser.add_argument(
            "--normalizer",
            choices=["local", "gms"],
            default="local",
            help="Use local deterministic extraction or SSAFY GMS OpenAI Responses API.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Save even when the same source_url and raw_hash already exist.",
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

        saved_count = 0
        skipped_count = 0
        dry_run_count = 0
        gms_client = self._build_gms_client(options["normalizer"])

        for candidate in candidates:
            raw_text = build_card_raw_text(candidate)
            raw_hash = compute_raw_hash(raw_text)
            source_url = candidate.source_url
            if source_url and not options["force"] and self._same_raw_hash_exists(source_url, raw_hash):
                skipped_count += 1
                continue

            document = RawCardDocument.from_candidate(candidate)
            payload = self._normalize_document(document, options["normalizer"], options["model_name"], gms_client)
            if options["dry_run"]:
                dry_run_count += 1
                quality = payload.get("quality")
                confidence = quality.get("extraction_confidence") if isinstance(quality, dict) else "unknown"
                self.safe_write(
                    f"{candidate.card_name} | raw_hash={raw_hash} | "
                    f"confidence={confidence} | unverified"
                )
                continue

            save_ai_normalized_candidate(candidate, payload, collection_url=options["url"])
            saved_count += 1

        if options["dry_run"]:
            self.safe_write(self.style.SUCCESS(f"Normalized {dry_run_count} candidates without saving."))
            return

        self.safe_write(
            self.style.SUCCESS(
                f"Saved {saved_count} AI-normalized candidates as unverified; skipped {skipped_count} unchanged."
            )
        )

    def _same_raw_hash_exists(self, source_url: str, raw_hash: str) -> bool:
        return CardCatalog.objects.filter(source_url=source_url, raw_hash=raw_hash).exists()

    def _build_gms_client(self, normalizer):
        if normalizer != "gms":
            return None
        try:
            return GMSClient.from_env()
        except GMSConfigurationError as exc:
            raise CommandError(str(exc)) from exc

    def _normalize_document(self, document, normalizer, model_name, gms_client):
        if normalizer == "local":
            return normalize_raw_document(document, model_name=model_name)
        if gms_client is None:
            raise CommandError("GMS client is not configured.")
        try:
            return gms_client.normalize_document(document)
        except (GMSRequestError, GMSResponseFormatError) as exc:
            raise CommandError(str(exc)) from exc

    def safe_write(self, message):
        safe_message = str(message).replace("\xa0", " ")
        self.stdout.write(safe_message.encode("cp949", errors="replace").decode("cp949"))
