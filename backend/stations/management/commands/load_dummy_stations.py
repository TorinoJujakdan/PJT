from django.core.management.base import BaseCommand
from django.utils import timezone

from stations.models import FuelPrice, GasStation

DUMMY_STATIONS = [
    {
        "external_station_id": "DUMMY-001",
        "name": "SmartFuel 강남역점",
        "brand": GasStation.Brand.GS,
        "address": "서울특별시 강남구 테헤란로 101",
        "latitude": "37.4980950",
        "longitude": "127.0276100",
        "is_self": True,
        "prices": {
            FuelPrice.FuelType.GASOLINE: 1645,
            FuelPrice.FuelType.DIESEL: 1515,
        },
    },
    {
        "external_station_id": "DUMMY-002",
        "name": "SmartFuel 역삼점",
        "brand": GasStation.Brand.SK,
        "address": "서울특별시 강남구 논현로 210",
        "latitude": "37.5007400",
        "longitude": "127.0365600",
        "is_self": False,
        "prices": {
            FuelPrice.FuelType.GASOLINE: 1660,
            FuelPrice.FuelType.DIESEL: 1530,
        },
    },
    {
        "external_station_id": "DUMMY-003",
        "name": "SmartFuel 선릉점",
        "brand": GasStation.Brand.S_OIL,
        "address": "서울특별시 강남구 선릉로 320",
        "latitude": "37.5045200",
        "longitude": "127.0489400",
        "is_self": True,
        "prices": {
            FuelPrice.FuelType.GASOLINE: 1638,
            FuelPrice.FuelType.DIESEL: 1508,
        },
    },
    {
        "external_station_id": "DUMMY-004",
        "name": "SmartFuel 잠실점",
        "brand": GasStation.Brand.HD_HYUNDAI,
        "address": "서울특별시 송파구 올림픽로 240",
        "latitude": "37.5132600",
        "longitude": "127.1001300",
        "is_self": False,
        "prices": {
            FuelPrice.FuelType.GASOLINE: 1629,
            FuelPrice.FuelType.DIESEL: 1499,
        },
    },
]


class Command(BaseCommand):
    help = "Load dummy gas station and fuel price data for local SmartFuel development."

    def handle(self, *args, **options):
        now = timezone.now()
        station_count = 0
        price_count = 0

        for item in DUMMY_STATIONS:
            prices = item.pop("prices")
            station, _created = GasStation.objects.update_or_create(
                external_station_id=item["external_station_id"],
                defaults=item,
            )
            station_count += 1

            for fuel_type, price_per_liter in prices.items():
                FuelPrice.objects.create(
                    station=station,
                    fuel_type=fuel_type,
                    price_per_liter=price_per_liter,
                    source=FuelPrice.Source.DUMMY,
                    collected_at=now,
                )
                price_count += 1

            item["prices"] = prices

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {station_count} stations and {price_count} fuel prices."
            )
        )

