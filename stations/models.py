from django.db import models

class GasStation(models.Model):
    id = models.CharField(max_length=20, primary_key=True, help_text="오피넷 주유소 고유 코드")
    name = models.CharField(max_length=100, help_text="주유소 상호명")
    brand = models.CharField(max_length=50, help_text="정유사 상표 (SK, GS 등)")
    address = models.CharField(max_length=255, help_text="주유소 도로명 주소")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, help_text="위도 (Y좌표)")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, help_text="경도 (X좌표)")
    gasoline_price = models.IntegerField(default=0, help_text="현재 휘발유 리터당 가격")
    diesel_price = models.IntegerField(default=0, help_text="현재 경유 리터당 가격")
    updated_at = models.DateTimeField(auto_now=True, help_text="유가 데이터 최종 업데이트 시각")

    def __str__(self):
        return f"[{self.brand}] {self.name}"
