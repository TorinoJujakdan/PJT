from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    NearbyStationQuerySerializer,
    RecommendationQuoteRequestSerializer,
    serialize_recommendation,
    serialize_station_candidate,
)
from .services import get_station_candidates, quote_travel_cost_recommendations


ERROR_MESSAGES = {
    "INVALID_LOCATION": "위도 또는 경도 값이 올바르지 않습니다.",
    "UNSUPPORTED_FUEL_TYPE": "지원하지 않는 유종입니다.",
    "INVALID_RADIUS": "검색 반경은 1km 이상 30km 이하여야 합니다.",
    "INVALID_TARGET_LITERS": "주유 예정량은 1L 이상 150L 이하여야 합니다.",
    "MISSING_VEHICLE_EFFICIENCY": "차량 연비 정보가 필요합니다.",
    "NO_STATION_CANDIDATE": "검색 반경 안에 주유소 후보가 없습니다.",
}


def error_response(code, http_status, details=None):
    return Response(
        {
            "code": code,
            "message": ERROR_MESSAGES[code],
            "details": details,
        },
        status=http_status,
    )


class NearbyStationAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        serializer = NearbyStationQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return self._validation_error(serializer.errors)

        data = serializer.validated_data
        candidates = get_station_candidates(
            location={"latitude": data["latitude"], "longitude": data["longitude"]},
            radius_km=data["radius_km"],
            fuel_type=data["fuel_type"],
        )

        if not candidates:
            return error_response("NO_STATION_CANDIDATE", status.HTTP_404_NOT_FOUND)

        stations = [serialize_station_candidate(candidate) for candidate in candidates]
        return Response(
            {
                "stations": stations,
                "meta": {
                    "count": len(stations),
                    "radius_km": data["radius_km"],
                },
            }
        )

    def _validation_error(self, errors):
        if "fuel_type" in errors:
            return error_response("UNSUPPORTED_FUEL_TYPE", status.HTTP_400_BAD_REQUEST, errors)
        if "radius_km" in errors:
            return error_response("INVALID_RADIUS", status.HTTP_400_BAD_REQUEST, errors)
        return error_response("INVALID_LOCATION", status.HTTP_400_BAD_REQUEST, errors)


class RecommendationQuoteAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RecommendationQuoteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return self._validation_error(serializer.errors)

        data = serializer.validated_data
        recommendations = quote_travel_cost_recommendations(
            location=data["location"],
            radius_km=data["radius_km"],
            fuel_type=data["fuel_type"],
            target_liters=data["target_liters"],
            fuel_efficiency_kmpl=data["vehicle"]["fuel_efficiency_kmpl"],
            travel_mode=data["travel_mode"],
        )

        if not recommendations:
            return error_response("NO_STATION_CANDIDATE", status.HTTP_404_NOT_FOUND)

        serialized_candidates = [serialize_recommendation(item) for item in recommendations]
        response_data = {
            "recommendation": serialized_candidates[0],
            "baseline": {
                "station_id": serialized_candidates[0]["station"]["station_id"],
                "effective_cost_without_card": serialized_candidates[0]["cost_breakdown"]["refuel_cost"],
            },
            "candidates": serialized_candidates if data["include_candidates"] else [],
            "meta": {
                "candidate_count": len(serialized_candidates),
                "radius_km": data["radius_km"],
                "distance_source": "haversine",
                "algorithm_version": "2026-05-18.v1-slice3",
            },
        }
        return Response(response_data)

    def _validation_error(self, errors):
        if "fuel_type" in errors:
            return error_response("UNSUPPORTED_FUEL_TYPE", status.HTTP_400_BAD_REQUEST, errors)
        if "target_liters" in errors:
            return error_response("INVALID_TARGET_LITERS", status.HTTP_400_BAD_REQUEST, errors)
        if "vehicle" in errors:
            return error_response("MISSING_VEHICLE_EFFICIENCY", status.HTTP_400_BAD_REQUEST, errors)
        if "radius_km" in errors:
            return error_response("INVALID_RADIUS", status.HTTP_400_BAD_REQUEST, errors)
        return error_response("INVALID_LOCATION", status.HTTP_400_BAD_REQUEST, errors)
