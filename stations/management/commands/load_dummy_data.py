import json
from django.core.management.base import BaseCommand
from stations.models import GasStation

class Command(BaseCommand):
    help = 'Load dummy gas station data (F811 Fallback)'

    def handle(self, *args, **kwargs):
        dummy_data = [
            {
                "id": "A0000001",
                "name": "강남셀프주유소",
                "brand": "SK에너지",
                "address": "서울 강남구 역삼로 123",
                "latitude": "37.498095",
                "longitude": "127.027610",
                "gasoline_price": 1650,
                "diesel_price": 1500
            },
            {
                "id": "A0000002",
                "name": "역삼직영주유소",
                "brand": "GS칼텍스",
                "address": "서울 강남구 테헤란로 456",
                "latitude": "37.500595",
                "longitude": "127.036610",
                "gasoline_price": 1600,
                "diesel_price": 1450
            },
            {
                "id": "A0000003",
                "name": "알뜰강남주유소",
                "brand": "알뜰주유소",
                "address": "서울 강남구 도곡로 789",
                "latitude": "37.492095",
                "longitude": "127.045610",
                "gasoline_price": 1550,
                "diesel_price": 1400
            }
        ]

        count = 0
        for item in dummy_data:
            obj, created = GasStation.objects.update_or_create(
                id=item['id'],
                defaults=item
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} dummy gas stations.'))
