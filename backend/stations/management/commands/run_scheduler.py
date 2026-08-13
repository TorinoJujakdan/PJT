from django.core.management.base import BaseCommand, CommandError

from stations.scheduler import build_scheduler


class Command(BaseCommand):
    help = "Run the dedicated SmartFuel APScheduler process."

    def handle(self, *args, **options):
        try:
            scheduler = build_scheduler()
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "SmartFuel scheduler started. Press Ctrl+C to stop it."
            )
        )
        try:
            scheduler.start()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("SmartFuel scheduler stopped."))
