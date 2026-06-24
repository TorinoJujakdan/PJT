from django.core.management.base import BaseCommand, CommandError

from cards.gemini_client import GeminiConfigurationError, load_gemini_config_from_env


class Command(BaseCommand):
    help = "Deprecated GMS key check; validates Gemini configuration without printing the API key."

    def handle(self, *args, **options):
        try:
            config = load_gemini_config_from_env()
        except GeminiConfigurationError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Gemini configuration is present. "
                f"model={config.model}, "
                f"base_url={config.base_url}, "
                f"timeout_seconds={config.timeout_seconds}, "
                f"max_output_tokens={config.max_output_tokens}. "
                "Gemini API credit usage is not exposed by this deprecated GMS command; "
                "per-call usageMetadata is stored by ingest_card_search_ai."
            )
        )
