import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("stations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="VehicleProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fuel_type", models.CharField(choices=[("gasoline", "Gasoline"), ("diesel", "Diesel"), ("lpg", "LPG"), ("premium_gasoline", "Premium gasoline")], max_length=32)),
                ("fuel_efficiency_kmpl", models.DecimalField(decimal_places=1, max_digits=4)),
                ("is_default", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vehicle_profiles", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-is_default", "-updated_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="vehicleprofile",
            index=models.Index(fields=["user", "is_default"], name="vehicles_ve_user_id_9b901a_idx"),
        ),
    ]
