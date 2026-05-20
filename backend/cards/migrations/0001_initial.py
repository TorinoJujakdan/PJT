# Generated for SmartFuel Slice 4 card policy APIs.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CardPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("card_name", models.CharField(max_length=120)),
                ("issuer_name", models.CharField(max_length=120)),
                (
                    "discount_type",
                    models.CharField(
                        choices=[
                            ("per_liter", "Per liter"),
                            ("percentage", "Percentage"),
                            ("fixed_amount", "Fixed amount"),
                        ],
                        max_length=32,
                    ),
                ),
                ("discount_value", models.DecimalField(decimal_places=2, max_digits=10)),
                ("brand_scope", models.CharField(default="all", max_length=32)),
                ("min_payment_amount", models.PositiveIntegerField(blank=True, null=True)),
                ("max_discount_amount", models.PositiveIntegerField(blank=True, null=True)),
                ("monthly_discount_limit", models.PositiveIntegerField(blank=True, null=True)),
                ("monthly_remaining_discount", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("manual", "Manual"),
                            ("naver_search", "Naver search"),
                            ("issuer", "Issuer"),
                            ("admin_seed", "Admin seed"),
                        ],
                        default="manual",
                        max_length=32,
                    ),
                ),
                (
                    "verification_status",
                    models.CharField(
                        choices=[
                            ("unverified", "Unverified"),
                            ("user_confirmed", "User confirmed"),
                            ("admin_verified", "Admin verified"),
                        ],
                        default="user_confirmed",
                        max_length=32,
                    ),
                ),
                ("card_image_url", models.URLField(blank=True)),
                ("source_url", models.URLField(blank=True)),
                ("source_title", models.CharField(blank=True, max_length=255)),
                ("user_memo", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="card_policies",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["issuer_name", "card_name", "id"],
            },
        ),
        migrations.CreateModel(
            name="CardBenefitSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("manual", "Manual"),
                            ("naver_search", "Naver search"),
                            ("issuer", "Issuer"),
                            ("admin_seed", "Admin seed"),
                        ],
                        max_length=32,
                    ),
                ),
                ("provider", models.CharField(default="naver", max_length=80)),
                ("source_url", models.URLField(blank=True)),
                ("source_title", models.CharField(blank=True, max_length=255)),
                ("source_summary", models.TextField(blank=True)),
                ("image_url", models.URLField(blank=True)),
                ("collected_at", models.DateTimeField(auto_now_add=True)),
                (
                    "card_policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="benefit_sources",
                        to="cards.cardpolicy",
                    ),
                ),
            ],
            options={
                "ordering": ["-collected_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="cardpolicy",
            index=models.Index(fields=["owner", "is_active"], name="cards_cardp_owner_i_708547_idx"),
        ),
        migrations.AddIndex(
            model_name="cardpolicy",
            index=models.Index(fields=["source_type", "verification_status"], name="cards_cardp_source__823a80_idx"),
        ),
        migrations.AddIndex(
            model_name="cardpolicy",
            index=models.Index(fields=["brand_scope"], name="cards_cardp_brand_s_51f59d_idx"),
        ),
    ]

