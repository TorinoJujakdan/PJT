from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from rest_framework.throttling import AnonRateThrottle

from cards.models import CardPolicy
from vehicles.models import VehicleProfile

from .serializers import (
    LocationSerializer,
    NearbyStationQuerySerializer,
    RecommendationQuoteRequestSerializer,
    StationRefreshRequestSerializer,
    serialize_recommendation,
    serialize_station_candidate,
)
from .services import get_station_candidates, quote_baseline_without_card, quote_travel_cost_recommendations


ERROR_MESSAGES = {
    "INVALID_LOCATION": "Latitude or longitude is invalid.",
    "UNSUPPORTED_FUEL_TYPE": "Fuel type is not supported.",
    "INVALID_RADIUS": "Radius is outside the allowed range.",
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


def refresh_opinet_prices_for_location(location, radius_km, fuel_type):
    """Best-effort Opinet refresh for the selected departure coordinate."""
    from .opinet_client import (
        OpinetClient,
        OpinetConfigurationError,
        OpinetMappingError,
        save_opinet_price_rows,
    )

    meta = {
        "source": "opinet",
        "rows": 0,
        "radius_km": radius_km,
        "request_location": {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
        },
    }

    try:
        client = OpinetClient()
    except OpinetConfigurationError:
        return {
            "status": "skipped",
            "reason": "OPINET_API_KEY_MISSING",
            "summary": None,
            "meta": meta,
        }

    try:
        rows = client.fetch_price_rows(
            latitude=location["latitude"],
            longitude=location["longitude"],
            radius_km=radius_km,
            fuel_type=fuel_type,
        )
    except OpinetMappingError as exc:
        return {
            "status": "failed",
            "reason": str(exc),
            "summary": None,
            "meta": meta,
        }

    summary = save_opinet_price_rows(rows)
    meta["rows"] = len(rows)
    return {
        "status": "ok" if rows else "empty",
        "reason": None,
        "summary": summary,
        "meta": meta,
    }


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
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = RecommendationQuoteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return self._validation_error(serializer.errors)

        data = serializer.validated_data
        fuel_efficiency_kmpl = self._resolve_fuel_efficiency(request, data)
        if fuel_efficiency_kmpl is None:
            return error_response("MISSING_VEHICLE_EFFICIENCY", status.HTTP_400_BAD_REQUEST)

        refresh_result = refresh_opinet_prices_for_location(
            location=data["location"],
            radius_km=min(data["radius_km"], 5),
            fuel_type=data["fuel_type"],
        )

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
            recommendation_priority=data["recommendation_priority"],
        )

        if not recommendations:
            return error_response("NO_STATION_CANDIDATE", status.HTTP_404_NOT_FOUND)

        recommended_station_id = recommendations[0].candidate.station.id
        serialized_recommendation = serialize_recommendation(
            recommendations[0],
            include_route_path=True,
        )
        serialized_candidates = [
            serialize_recommendation(
                item,
                include_route_path=item.candidate.station.id == recommended_station_id,
            )
            for item in recommendations
        ]
        response_data = {
            "recommendation": serialized_recommendation,
            "baseline": quote_baseline_without_card(recommendations),
            "candidates": serialized_candidates if data["include_candidates"] else [],
            "meta": {
                "candidate_count": len(serialized_candidates),
                "radius_km": data["radius_km"],
                "distance_source": recommendations[0].distance_source if recommendations else "haversine",
                "recommendation_priority": data["recommendation_priority"],
                "station_data_state": "database",
                "external_station_refresh": refresh_result["status"],
                "external_station_refresh_reason": refresh_result.get("reason"),
                "external_station_refresh_summary": refresh_result.get("summary"),
                "external_station_refresh_meta": refresh_result.get("meta"),
                "algorithm_version": "2026-06-22.v4-priority-ranking",
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
        return (
            CardPolicy.objects.filter(owner=request.user, is_active=True)
            .select_related("linked_catalog")
            .prefetch_related("linked_catalog__benefit_tiers")
        )

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


class GeocodeAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        query = request.query_params.get("query", "").strip()[:120]
        if not query:
            return Response(
                {
                    "code": "MISSING_QUERY",
                    "message": "검색어(query) 파라미터가 누락되었습니다."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        from .geocoding_service import geocode_query_with_meta

        payload = geocode_query_with_meta(query)
        return Response(payload)


class ReverseGeocodeAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        serializer = LocationSerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response("INVALID_LOCATION", status.HTTP_400_BAD_REQUEST, serializer.errors)

        from .geocoding_service import reverse_geocode_with_meta

        data = serializer.validated_data
        payload = reverse_geocode_with_meta(data["latitude"], data["longitude"])
        return Response(payload)


class RefreshNearbyStationsAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = StationRefreshRequestSerializer(data=request.data)
        if not serializer.is_valid():
            if "fuel_type" in serializer.errors:
                return error_response("UNSUPPORTED_FUEL_TYPE", status.HTTP_400_BAD_REQUEST, serializer.errors)
            if "radius_km" in serializer.errors:
                return error_response("INVALID_RADIUS", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return error_response("INVALID_LOCATION", status.HTTP_400_BAD_REQUEST, serializer.errors)

        data = serializer.validated_data
        refresh_result = refresh_opinet_prices_for_location(
            location=data["location"],
            radius_km=data["radius_km"],
            fuel_type=data.get("fuel_type"),
        )
        response_status = status.HTTP_400_BAD_REQUEST if refresh_result["status"] == "failed" else status.HTTP_200_OK
        return Response(refresh_result, status=response_status)
