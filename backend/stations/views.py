from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from cards.models import CardPolicy
from vehicles.models import VehicleProfile

from .serializers import (
    NearbyStationQuerySerializer,
    RecommendationQuoteRequestSerializer,
    serialize_recommendation,
    serialize_station_candidate,
)
from .services import get_station_candidates, quote_baseline_without_card, quote_travel_cost_recommendations


ERROR_MESSAGES = {
    "INVALID_LOCATION": "Latitude or longitude is invalid.",
    "UNSUPPORTED_FUEL_TYPE": "Fuel type is not supported.",
    "INVALID_RADIUS": "Radius must be between 1km and 30km.",
    "INVALID_TARGET_LITERS": "Target liters must be between 1L and 150L.",
    "INVALID_CARD_POLICY": "Card policy input is invalid.",
    "MISSING_VEHICLE_EFFICIENCY": "Vehicle fuel efficiency is required.",
    "NO_STATION_CANDIDATE": "No station candidate exists inside the search radius.",
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
    permission_classes = []

    def post(self, request):
        serializer = RecommendationQuoteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return self._validation_error(serializer.errors)

        data = serializer.validated_data
        fuel_efficiency_kmpl = self._resolve_fuel_efficiency(request, data)
        if fuel_efficiency_kmpl is None:
            return error_response("MISSING_VEHICLE_EFFICIENCY", status.HTTP_400_BAD_REQUEST)

        saved_cards = self._get_saved_cards(request)
        user_cards = list(saved_cards) + list(data["cards"])
        recommendations = quote_travel_cost_recommendations(
            location=data["location"],
            radius_km=data["radius_km"],
            fuel_type=data["fuel_type"],
            target_liters=data["target_liters"],
            fuel_efficiency_kmpl=fuel_efficiency_kmpl,
            travel_mode=data["travel_mode"],
            user_cards=user_cards,
        )

        if not recommendations:
            return error_response("NO_STATION_CANDIDATE", status.HTTP_404_NOT_FOUND)

        serialized_candidates = [serialize_recommendation(item) for item in recommendations]
        response_data = {
            "recommendation": serialized_candidates[0],
            "baseline": quote_baseline_without_card(recommendations),
            "candidates": serialized_candidates if data["include_candidates"] else [],
            "meta": {
                "candidate_count": len(serialized_candidates),
                "radius_km": data["radius_km"],
                "distance_source": "haversine",
                "algorithm_version": "2026-05-19.v1-slice6-explanation",
                "map_display": {
                    "coordinate_source": "station_summary",
                    "rank_source": "backend_recommendation_order",
                    "frontend_recalculation_allowed": False,
                },
            },
        }
        return Response(response_data)

    def _get_saved_cards(self, request):
        if not request.user or not request.user.is_authenticated:
            return []
        return CardPolicy.objects.filter(owner=request.user, is_active=True)

    def _resolve_fuel_efficiency(self, request, data):
        vehicle = data.get("vehicle")
        if vehicle:
            return vehicle["fuel_efficiency_kmpl"]

        if not request.user or not request.user.is_authenticated:
            return None

        profile = VehicleProfile.objects.filter(user=request.user, is_default=True).first()
        if profile is None:
            return None
        return float(profile.fuel_efficiency_kmpl)

    def _validation_error(self, errors):
        if "fuel_type" in errors:
            return error_response("UNSUPPORTED_FUEL_TYPE", status.HTTP_400_BAD_REQUEST, errors)
        if "target_liters" in errors:
            return error_response("INVALID_TARGET_LITERS", status.HTTP_400_BAD_REQUEST, errors)
        if "cards" in errors:
            return error_response("INVALID_CARD_POLICY", status.HTTP_400_BAD_REQUEST, errors)
        if "vehicle" in errors:
            return error_response("MISSING_VEHICLE_EFFICIENCY", status.HTTP_400_BAD_REQUEST, errors)
        if "radius_km" in errors:
            return error_response("INVALID_RADIUS", status.HTTP_400_BAD_REQUEST, errors)
        return error_response("INVALID_LOCATION", status.HTTP_400_BAD_REQUEST, errors)
