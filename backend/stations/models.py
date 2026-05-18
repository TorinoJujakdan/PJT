from django.db import models


class GasStation(models.Model):
    class Brand(models.TextChoices):
        SK = "SK", "SK"
        GS = "GS", "GS"
        S_OIL = "S_OIL", "S-OIL"
        HD_HYUNDAI = "HD_HYUNDAI", "HD Hyundai Oilbank"
        OTHER = "OTHER", "Other"

    external_station_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    brand = models.CharField(max_length=32, choices=Brand.choices, default=Brand.OTHER)
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    is_self = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["brand"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.brand})"


class FuelPrice(models.Model):
    class FuelType(models.TextChoices):
        GASOLINE = "gasoline", "Gasoline"
        DIESEL = "diesel", "Diesel"
        LPG = "lpg", "LPG"
        PREMIUM_GASOLINE = "premium_gasoline", "Premium gasoline"

    class Source(models.TextChoices):
        DUMMY = "dummy", "Dummy"
        OPINET = "opinet", "Opinet"

    station = models.ForeignKey(GasStation, related_name="fuel_prices", on_delete=models.CASCADE)
    fuel_type = models.CharField(max_length=32, choices=FuelType.choices)
    price_per_liter = models.PositiveIntegerField()
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.DUMMY)
    collected_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["station_id", "fuel_type", "-collected_at"]
        indexes = [
            models.Index(fields=["fuel_type", "price_per_liter"]),
            models.Index(fields=["station", "fuel_type", "-collected_at"]),
        ]

    def __str__(self):
        return f"{self.station.name} {self.fuel_type} {self.price_per_liter}"

