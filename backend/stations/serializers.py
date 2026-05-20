from rest_framework import serializers

from cards.models import CardPolicy

from .models import FuelPrice


class NearbyStationQuerySerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    fuel_type = serializers.ChoiceField(choices=FuelPrice.FuelType.choices)
    radius_km = serializers.FloatField(min_value=1, max_value=30, required=False, default=15)


class LocationSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class RecommendationCardPolicySerializer(serializers.Serializer):
    card_id = serializers.CharField(required=False, allow_blank=True)
    card_name = serializers.CharField()
    issuer_name = serializers.CharField()
    discount_type = serializers.ChoiceField(choices=CardPolicy.DiscountType.choices)
    discount_value = serializers.FloatField(min_value=0)
    brand_scope = serializers.CharField(required=False, allow_blank=True, default="all")
    min_payment_amount = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    max_discount_amount = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    monthly_remaining_discount = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    source_type = serializers.ChoiceField(
        choices=CardPolicy.SourceType.choices,
        required=False,
        default=CardPolicy.SourceType.MANUAL,
    )
    verification_status = serializers.ChoiceField(
        choices=CardPolicy.VerificationStatus.choices,
        required=False,
        default=CardPolicy.VerificationStatus.USER_CONFIRMED,
    )
    card_image_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    source_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        if attrs["discount_type"] == CardPolicy.DiscountType.PERCENTAGE and attrs["discount_value"] > 100:
            raise serializers.ValidationError({"discount_value": "percentage discount cannot exceed 100."})
        return attrs


class RecommendationQuoteRequestSerializer(serializers.Serializer):
    location = LocationSerializer()
    fuel_type = serializers.ChoiceField(choices=FuelPrice.FuelType.choices)
    target_liters = serializers.FloatField(min_value=1, max_value=150)
    radius_km = serializers.FloatField(min_value=1, max_value=30, required=False, default=15)
    travel_mode = serializers.ChoiceField(
        choices=["round_trip", "one_way"],
        required=False,
        default="round_trip",
    )
    vehicle = serializers.DictField(required=False)
    cards = RecommendationCardPolicySerializer(many=True, required=False, default=list)
    include_candidates = serializers.BooleanField(required=False, default=True)

    def validate_vehicle(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Vehicle must be an object.")

        fuel_efficiency = value.get("fuel_efficiency_kmpl")
        if fuel_efficiency is None:
            raise serializers.ValidationError("fuel_efficiency_kmpl is required.")

        try:
            fuel_efficiency = float(fuel_efficiency)
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError("fuel_efficiency_kmpl must be a number.") from exc

        if fuel_efficiency < 1 or fuel_efficiency > 50:
            raise serializers.ValidationError("fuel_efficiency_kmpl must be between 1 and 50.")

        return {"fuel_efficiency_kmpl": fuel_efficiency}


class StationSummarySerializer(serializers.Serializer):
    station_id = serializers.IntegerField()
    name = serializers.CharField()
    brand = serializers.CharField()
    address = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    distance_km = serializers.FloatField()
    distance_source = serializers.CharField()
    fuel_type = serializers.CharField()
    fuel_price_per_liter = serializers.IntegerField()


def serialize_station_candidate(candidate):
    station = candidate.station
    return {
        "station_id": station.id,
        "name": station.name,
        "brand": station.brand,
        "address": station.address,
        "latitude": float(station.latitude),
        "longitude": float(station.longitude),
        "distance_km": candidate.distance_km,
        "distance_source": "haversine",
        "fuel_type": candidate.fuel_type,
        "fuel_price_per_liter": candidate.fuel_price_per_liter,
    }


def serialize_recommendation(item):
    return {
        "station": serialize_station_candidate(item.candidate),
        "cost_breakdown": {
            "target_liters": item.target_liters,
            "refuel_cost": item.refuel_cost,
            "card_discount_amount": item.card_discount_amount,
            "travel_cost": item.travel_cost,
            "effective_total_cost": item.effective_total_cost,
            "estimated_saving": item.estimated_saving,
        },
        "selected_card": item.selected_card,
        "reason": item.reason,
    }
