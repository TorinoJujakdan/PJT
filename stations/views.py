from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import GasStation
from .serializers import RecommendationResponseSerializer
from .services import calculate_recommendations

class RecommendationAPIView(APIView):
    def get(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lng = float(request.query_params.get('lng'))
            target_amount = int(request.query_params.get('target_amount'))
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid parameters. 'lat', 'lng', and 'target_amount' are required and must be numbers."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. DB 레벨 1차 필터링 (Bounding Box - 15km 반경 대략적 계산)
        # 위도/경도 1도는 약 111km. 15km는 약 0.135도.
        lat_margin = 0.135
        lng_margin = 0.135
        
        stations = GasStation.objects.filter(
            latitude__range=(lat - lat_margin, lat + lat_margin),
            longitude__range=(lng - lng_margin, lng + lng_margin)
        )

        # SA4의 핵심 로직(2단계 필터링 및 추천 연산) 호출
        recommendations = calculate_recommendations(lat, lng, target_amount, stations, request.user)

        # 직렬화
        serializer = RecommendationResponseSerializer(data=recommendations, many=True)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
