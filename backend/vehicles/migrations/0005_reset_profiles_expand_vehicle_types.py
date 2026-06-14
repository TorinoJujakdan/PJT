from django.db import migrations, models


def delete_vehicle_profiles(apps, schema_editor):
    vehicle_profile = apps.get_model("vehicles", "VehicleProfile")
    vehicle_profile.objects.all().delete()


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("vehicles", "0004_vehicleprofile_vehicles_one_default_per_user"),
    ]

    operations = [
        migrations.RunPython(delete_vehicle_profiles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="vehicleprofile",
            name="vehicle_type",
            field=models.CharField(
                choices=[
                    ("sedan", "Sedan"),
                    ("suv", "SUV"),
                    ("rv_mpv", "RV / MPV"),
                    ("sports_coupe", "Sports car / Coupe"),
                    ("hatchback", "Hatchback"),
                    ("wagon", "Wagon"),
                    ("convertible", "Convertible / Roadster"),
                    ("pickup", "Pickup truck"),
                    ("micro_city", "Micro / City car"),
                ],
                max_length=20,
            ),
        ),
    ]
