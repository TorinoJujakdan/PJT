from django.core.management.base import BaseCommand, CommandError

from stations.opinet_client import (
    OpinetClient,
    OpinetConfigurationError,
    OpinetMappingError,
    OPINET_MAX_RADIUS_KM,
    save_opinet_price_rows,
)


class Command(BaseCommand):
    help = "Synchronize Opinet fuel price data into local FuelPrice rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate Opinet configuration without writing fuel price rows.",
        )
        parser.add_argument(
            "--health-check",
            action="store_true",
            help="Call the official Opinet average-price endpoint without writing fuel price rows.",
        )
        parser.add_argument("--latitude", type=float, help="WGS84 latitude to search around.")
        parser.add_argument("--longitude", type=float, help="WGS84 longitude to search around.")
        parser.add_argument(
            "--radius-km",
            type=float,
            default=OPINET_MAX_RADIUS_KM,
            help=f"Search radius in km. Opinet aroundAll is capped at {OPINET_MAX_RADIUS_KM:g}km.",
        )
        parser.add_argument(
            "--fuel-type",
            choices=["gasoline", "diesel", "lpg", "premium_gasoline"],
            help="Optional SmartFuel fuel type to synchronize.",
        )

    def handle(self, *args, **options):
        try:
            client = OpinetClient()
        except OpinetConfigurationError as exc:
            raise CommandError(str(exc)) from exc

        if options["health_check"]:
            average_rows = client.fetch_average_price_rows()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Opinet average-price endpoint ok. {len(average_rows)} rows returned."
                )
            )
            return

        if options["dry_run"]:
            self._require_location(options)
            rows = client.fetch_price_rows(
                latitude=options["latitude"],
                longitude=options["longitude"],
                radius_km=options["radius_km"],
                fuel_type=options["fuel_type"],
            )
            self.stdout.write(self.style.SUCCESS(f"Opinet configuration ok. {len(rows)} rows available."))
            return

        self._require_location(options)
        try:
            rows = client.fetch_price_rows(
                latitude=options["latitude"],
                longitude=options["longitude"],
                radius_km=options["radius_km"],
                fuel_type=options["fuel_type"],
            )
        except OpinetMappingError as exc:
            raise CommandError(str(exc)) from exc

        if not rows:
            self.stdout.write(self.style.WARNING("No rows returned from Opinet API."))
            return

        summary = save_opinet_price_rows(rows)
        self.stdout.write(
            self.style.SUCCESS(
                "Opinet ingestion complete. "
                f"Created {summary['stations_created']} new stations, "
                f"saved {summary['prices_created']} price entries, "
                f"skipped {summary['rows_skipped']} rows."
            )
        )

    def _require_location(self, options):
        if options["latitude"] is None or options["longitude"] is None:
            raise CommandError("--latitude and --longitude are required for station-level Opinet synchronization.")
