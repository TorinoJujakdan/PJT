from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("vehicles", "0003_reset_profiles_add_name_vehicle_type"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="vehicleprofile",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_default", True)),
                fields=("user",),
                name="vehicles_one_default_per_user",
            ),
        ),
    ]
