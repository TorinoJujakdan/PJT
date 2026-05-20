from django.conf import settings
from django.db import models


class CardPolicy(models.Model):
    class DiscountType(models.TextChoices):
        PER_LITER = "per_liter", "Per liter"
        PERCENTAGE = "percentage", "Percentage"
        FIXED_AMOUNT = "fixed_amount", "Fixed amount"

    class SourceType(models.TextChoices):
        MANUAL = "manual", "Manual"
        SELENIUM = "selenium", "Selenium"
        NAVER_SEARCH = "naver_search", "Naver search"
        ISSUER = "issuer", "Issuer"
        ADMIN_SEED = "admin_seed", "Admin seed"

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        USER_CONFIRMED = "user_confirmed", "User confirmed"
        ADMIN_VERIFIED = "admin_verified", "Admin verified"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="card_policies", on_delete=models.CASCADE)
    card_name = models.CharField(max_length=120)
    issuer_name = models.CharField(max_length=120)
    discount_type = models.CharField(max_length=32, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    brand_scope = models.CharField(max_length=32, default="all")
    min_payment_amount = models.PositiveIntegerField(null=True, blank=True)
    max_discount_amount = models.PositiveIntegerField(null=True, blank=True)
    monthly_discount_limit = models.PositiveIntegerField(null=True, blank=True)
    monthly_remaining_discount = models.PositiveIntegerField(null=True, blank=True)
    source_type = models.CharField(max_length=32, choices=SourceType.choices, default=SourceType.MANUAL)
    verification_status = models.CharField(
        max_length=32,
        choices=VerificationStatus.choices,
        default=VerificationStatus.USER_CONFIRMED,
    )
    card_image_url = models.URLField(blank=True)
    source_url = models.URLField(blank=True)
    source_title = models.CharField(max_length=255, blank=True)
    user_memo = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["issuer_name", "card_name", "id"]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["source_type", "verification_status"]),
            models.Index(fields=["brand_scope"]),
        ]

    def __str__(self):
        return f"{self.issuer_name} {self.card_name}"

    @property
    def can_affect_recommendation(self):
        return self.source_type == self.SourceType.MANUAL or self.verification_status in {
            self.VerificationStatus.USER_CONFIRMED,
            self.VerificationStatus.ADMIN_VERIFIED,
        }


class CardCatalog(models.Model):
    card_name = models.CharField(max_length=120)
    issuer_name = models.CharField(max_length=120, blank=True)
    discount_type = models.CharField(
        max_length=32,
        choices=CardPolicy.DiscountType.choices,
        default=CardPolicy.DiscountType.PER_LITER,
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    brand_scope = models.CharField(max_length=32, default="all")
    min_payment_amount = models.PositiveIntegerField(null=True, blank=True)
    max_discount_amount = models.PositiveIntegerField(null=True, blank=True)
    monthly_discount_limit = models.PositiveIntegerField(null=True, blank=True)
    monthly_remaining_discount = models.PositiveIntegerField(null=True, blank=True)
    card_image_url = models.URLField(blank=True)
    source_url = models.URLField(blank=True, unique=True)
    source_title = models.CharField(max_length=255, blank=True)
    source_type = models.CharField(
        max_length=32,
        choices=CardPolicy.SourceType.choices,
        default=CardPolicy.SourceType.SELENIUM,
    )
    verification_status = models.CharField(
        max_length=32,
        choices=CardPolicy.VerificationStatus.choices,
        default=CardPolicy.VerificationStatus.UNVERIFIED,
    )
    raw_summary = models.TextField(blank=True)
    confidence = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["issuer_name", "card_name", "id"]
        indexes = [
            models.Index(fields=["source_type", "verification_status"]),
            models.Index(fields=["issuer_name", "card_name"]),
        ]

    def __str__(self):
        return f"{self.issuer_name} {self.card_name}".strip()


class CardBenefitSource(models.Model):
    card_policy = models.ForeignKey(CardPolicy, related_name="benefit_sources", on_delete=models.CASCADE)
    source_type = models.CharField(max_length=32, choices=CardPolicy.SourceType.choices)
    provider = models.CharField(max_length=80, default="naver")
    source_url = models.URLField(blank=True)
    source_title = models.CharField(max_length=255, blank=True)
    source_summary = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    collected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-collected_at", "id"]

    def __str__(self):
        return f"{self.provider}: {self.source_title or self.source_url}"
