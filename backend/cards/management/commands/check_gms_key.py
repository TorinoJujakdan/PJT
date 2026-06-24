from django.core.management.base import BaseCommand, CommandError

from cards.gms_client import GMSClient, GMSConfigurationError, GMSRequestError, GMSResponseFormatError


class Command(BaseCommand):
    help = "Check SSAFY GMS key credit information without printing the API key."

    def handle(self, *args, **options):
        try:
            key_info = GMSClient.from_env().get_key_info()
        except (GMSConfigurationError, GMSRequestError, GMSResponseFormatError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "GMS key is valid: "
                f"total={key_info.total_credit}, "
                f"used={key_info.used_credit}, "
                f"remain={key_info.remain_credit}, "
                f"expired={key_info.expired_date}"
            )
        )
