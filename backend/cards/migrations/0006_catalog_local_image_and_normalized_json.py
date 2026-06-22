# Generated manually for SmartFuel card ingestion image persistence.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cards", "0005_add_owner_to_cardingestiontask"),
    ]

    operations = [
        migrations.AddField(
            model_name="cardcatalog",
            name="card_image_original_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="cardcatalog",
            name="card_image_file",
            field=models.FileField(blank=True, upload_to="card_images/catalog/"),
        ),
        migrations.AddField(
            model_name="cardcatalog",
            name="normalized_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="cardpolicy",
            name="card_image_original_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="cardpolicy",
            name="card_image_file",
            field=models.FileField(blank=True, upload_to="card_images/policies/"),
        ),
    ]
