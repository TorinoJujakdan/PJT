from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cards", "0006_catalog_local_image_and_normalized_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="cardcatalog",
            name="raw_hash",
            field=models.CharField(blank=True, db_index=True, max_length=80),
        ),
    ]
