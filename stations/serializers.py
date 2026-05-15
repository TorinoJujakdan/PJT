from rest_framework import serializers
from .models import GasStation

class RecommendationResponseSerializer(serializers.Serializer):
    station_id = serializers.CharField()
    name = serializers.CharField()
    brand = serializers.CharField()
    original_price = serializers.IntegerField(help_text="오피넷 원래 가격")
    final_price = serializers.IntegerField(help_text="카드 할인 적용된 최종 결제 예상 금액")
    saved_amount = serializers.IntegerField(help_text="일반 결제 대비 총 절약된 금액(원)")
    distance_km = serializers.FloatField(help_text="주행 거리(km)")
    navigation_url = serializers.CharField(help_text="네비게이션 연동 URL")
