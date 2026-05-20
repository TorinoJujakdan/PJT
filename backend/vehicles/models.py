from django.conf import settings
from django.db import models

from stations.models import FuelPrice


class VehicleProfile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="vehicle_profiles", on_delete=models.CASCADE)
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

    def __str__(self):
        return f"{self.user} {self.fuel_type} {self.fuel_efficiency_kmpl}km/L"
