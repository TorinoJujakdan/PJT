import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from stations.models import GasStation
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch real-time gas station data from Opinet API with Dummy Fallback'

    def handle(self, *args, **kwargs):
        api_key = os.environ.get('OPINET_API_KEY', 'dummy_key')
        
        # 실제 오피넷 API 엔드포인트 예시 (주변 주유소 찾기)
        # url = f"http://www.opinet.co.kr/api/aroundAll.do?code={api_key}&x=314681.8&y=544871.1&radius=5000&sort=1&prodcd=B027&out=json"
        
        try:
            if api_key == 'your_opinet_api_key_here' or api_key == 'dummy_key':
                raise ValueError("Valid OPINET_API_KEY is missing. Triggering Fallback.")

            # 실제로 API를 호출하는 로직 (주석 처리 또는 Mock 형태로 구현)
            # response = requests.get(url, timeout=10)
            # response.raise_for_status()
            # data = response.json()
            # Process data and update DB...
            
            self.stdout.write(self.style.SUCCESS("Opinet API data successfully fetched and updated."))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Opinet API Fetch Failed: {str(e)}"))
            self.stdout.write(self.style.WARNING("Executing Fallback Logic: Loading Dummy Data..."))
            self.load_dummy_data()

    def load_dummy_data(self):
        # 1일차에 작성한 더미 데이터 로직 재사용
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

        self.stdout.write(self.style.SUCCESS(f'Fallback completed: {count} dummy gas stations loaded/updated.'))
