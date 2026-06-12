from rest_framework import serializers

from .models import VehicleProfile


class VehicleProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleProfile
        fields = [
            "id",
            "name",
            "vehicle_type",
            "fuel_type",
            "fuel_efficiency_kmpl",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_default", "created_at", "updated_at"]

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("name must not be blank.")
        return name

    def validate_fuel_efficiency_kmpl(self, value):
        if value < 1 or value > 50:
            raise serializers.ValidationError("fuel_efficiency_kmpl must be between 1.0 and 50.0.")
        return value
