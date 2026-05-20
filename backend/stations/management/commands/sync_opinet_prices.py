from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from stations.models import GasStation, FuelPrice
from stations.opinet_client import (
    OpinetClient,
    OpinetConfigurationError,
    OpinetMappingError,
    normalize_opinet_station_row,
    normalize_opinet_price_row,
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
            rows = client.fetch_price_rows()
            self.stdout.write(self.style.SUCCESS(f"Opinet configuration ok. {len(rows)} rows available."))
            return

        rows = client.fetch_price_rows()
        if not rows:
            self.stdout.write(self.style.WARNING("No rows returned from Opinet API."))
            return

        now = timezone.now()
        station_count = 0
        price_count = 0

        for row in rows:
            try:
                # 1. 주유소 정보 매핑 및 저장/업데이트
                station_data = normalize_opinet_station_row(row)
                external_id = station_data.pop("external_station_id")
                
                # GasStation의 실제 DB 필드만 필터링하여 defaults로 전달
                allowed_fields = {"name", "brand", "address", "latitude", "longitude", "is_self"}
                defaults = {k: v for k, v in station_data.items() if k in allowed_fields}
                
                # address 필드가 없을 수 있으므로 폴백 처리
                if "address" not in defaults or not defaults["address"]:
                    defaults["address"] = "주소 정보 없음"

                station, created = GasStation.objects.update_or_create(
                    external_station_id=external_id,
                    defaults=defaults,
                )
                if created:
                    station_count += 1

                # 2. 가격 정보 매핑 및 저장
                price_data = normalize_opinet_price_row(row)
                FuelPrice.objects.create(
                    station=station,
                    fuel_type=price_data["fuel_type"],
                    price_per_liter=price_data["price_per_liter"],
                    source=FuelPrice.Source.OPINET,
                    collected_at=now,
                )
                price_count += 1
            except (OpinetMappingError, ValueError) as exc:
                self.stdout.write(self.style.WARNING(f"Skipping row due to mapping error: {exc}"))
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"Opinet Ingestion complete. Created {station_count} new stations, saved {price_count} price entries."
            )
        )
