from django.conf import settings
from django.db import models

from stations.models import FuelPrice


class VehicleProfile(models.Model):
    class VehicleType(models.TextChoices):
        COMPACT = "compact", "Compact"
        SEDAN = "sedan", "Sedan"
        SUV = "suv", "SUV"
        LARGE_RV = "large_rv", "Large RV"
        SPORTS = "sports", "Sports"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="vehicle_profiles", on_delete=models.CASCADE)
    name = models.CharField(max_length=40)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices)
    fuel_type = models.CharField(max_length=32, choices=FuelPrice.FuelType.choices)
    fuel_efficiency_kmpl = models.DecimalField(max_digits=4, decimal_places=1)
    is_default = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at", "id"]
        indexes = [
            models.Index(fields=["user", "is_default"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="vehicles_one_default_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user} {self.name} {self.fuel_efficiency_kmpl}km/L"
