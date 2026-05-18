# Generated for SmartFuel Slice 1.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GasStation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_station_id", models.CharField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=120)),
                (
                    "brand",
                    models.CharField(
                        choices=[
                            ("SK", "SK"),
                            ("GS", "GS"),
                            ("S_OIL", "S-OIL"),
                            ("HD_HYUNDAI", "HD Hyundai Oilbank"),
                            ("OTHER", "Other"),
                        ],
                        default="OTHER",
                        max_length=32,
                    ),
                ),
                ("address", models.CharField(max_length=255)),
                ("latitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("longitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("is_self", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="FuelPrice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "fuel_type",
                    models.CharField(
                        choices=[
                            ("gasoline", "Gasoline"),
                            ("diesel", "Diesel"),
                            ("lpg", "LPG"),
                            ("premium_gasoline", "Premium gasoline"),
                        ],
                        max_length=32,
                    ),
                ),
                ("price_per_liter", models.PositiveIntegerField()),
                (
                    "source",
                    models.CharField(
                        choices=[("dummy", "Dummy"), ("opinet", "Opinet")],
                        default="dummy",
                        max_length=32,
                    ),
                ),
                ("collected_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "station",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fuel_prices",
                        to="stations.gasstation",
                    ),
                ),
            ],
            options={
                "ordering": ["station_id", "fuel_type", "-collected_at"],
            },
        ),
        migrations.AddIndex(
            model_name="gasstation",
            index=models.Index(fields=["latitude", "longitude"], name="stations_ga_latitud_1d5c86_idx"),
        ),
        migrations.AddIndex(
            model_name="gasstation",
            index=models.Index(fields=["brand"], name="stations_ga_brand_6f57a8_idx"),
        ),
        migrations.AddIndex(
            model_name="fuelprice",
            index=models.Index(fields=["fuel_type", "price_per_liter"], name="stations_fu_fuel_ty_e56c8c_idx"),
        ),
        migrations.AddIndex(
            model_name="fuelprice",
            index=models.Index(fields=["station", "fuel_type", "-collected_at"], name="stations_fu_station_e29b10_idx"),
        ),
    ]

