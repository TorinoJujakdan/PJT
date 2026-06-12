from django.db import migrations, models


def delete_vehicle_profiles(apps, schema_editor):
    vehicle_profile = apps.get_model("vehicles", "VehicleProfile")
    vehicle_profile.objects.all().delete()


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("vehicles", "0002_rename_vehicles_ve_user_id_9b901a_idx_vehicles_ve_user_id_24c28e_idx"),
    ]

    operations = [
        migrations.RunPython(delete_vehicle_profiles, migrations.RunPython.noop),
        migrations.AddField(
            model_name="vehicleprofile",
            name="name",
            field=models.CharField(default="", max_length=40),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="vehicleprofile",
            name="vehicle_type",
            field=models.CharField(
                choices=[
                    ("compact", "Compact"),
                    ("sedan", "Sedan"),
                    ("suv", "SUV"),
                    ("large_rv", "Large RV"),
                    ("sports", "Sports"),
                ],
                default="sedan",
                max_length=20,
            ),
            preserve_default=False,
        ),
    ]
