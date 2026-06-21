from django.conf import settings
from django.db import models


class CardPolicy(models.Model):
    """
    사용자가 소유한 카드 및 수동 등록한 카드 혜택 정보를 저장합니다.
    (UI의 '소유 할인 카드 관리' 대응)
    """
    class DiscountType(models.TextChoices):
        PER_LITER = "per_liter", "Per liter"
        PERCENTAGE = "percentage", "Percentage"
        FIXED_AMOUNT = "fixed_amount", "Fixed amount"

    class SourceType(models.TextChoices):
        MANUAL = "manual", "Manual"
        CATALOG = "catalog", "Catalog"
        SELENIUM = "selenium", "Selenium"
        NAVER_SEARCH = "naver_search", "Naver search"
        ISSUER = "issuer", "Issuer"
        ADMIN_SEED = "admin_seed", "Admin seed"

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        USER_CONFIRMED = "user_confirmed", "User confirmed"
        ADMIN_VERIFIED = "admin_verified", "Admin verified"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="card_policies", on_delete=models.CASCADE)
    linked_catalog = models.ForeignKey(
        "CardCatalog", null=True, blank=True, related_name="linked_policies", on_delete=models.SET_NULL
    )
    card_name = models.CharField(max_length=120)
    issuer_name = models.CharField(max_length=120)
    discount_type = models.CharField(max_length=32, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    brand_scope = models.CharField(max_length=32, default="all")
    min_payment_amount = models.PositiveIntegerField(null=True, blank=True)
    max_discount_amount = models.PositiveIntegerField(null=True, blank=True)
    monthly_discount_limit = models.PositiveIntegerField(null=True, blank=True)
    monthly_remaining_discount = models.PositiveIntegerField(null=True, blank=True)
    previous_month_spending = models.PositiveIntegerField(
        null=True, blank=True, help_text="전월 실적 또는 이번 달 카드 사용액 (추천 알고리즘 Tier 매칭용)"
    )
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
        return self.source_type in {self.SourceType.MANUAL, self.SourceType.CATALOG} or self.verification_status in {
            self.VerificationStatus.USER_CONFIRMED,
            self.VerificationStatus.ADMIN_VERIFIED,
        }


class CardCatalog(models.Model):
    """
    네이버 등에서 수집한 마스터 카드 정보 (검색용)
    구체적인 혜택 내용은 CardBenefitTier로 1:N 분리.
    """
    card_name = models.CharField(max_length=120)
    issuer_name = models.CharField(max_length=120, blank=True)
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


class CardBenefitTier(models.Model):
    """
    마스터 카드의 전월 실적 및 유종별 계단식 혜택 구간
    """
    card_catalog = models.ForeignKey(CardCatalog, related_name="benefit_tiers", on_delete=models.CASCADE)
    fuel_type = models.CharField(max_length=32, help_text="GASOLINE, DIESEL, LPG, EV, ALL 등")
    min_performance_amount = models.PositiveIntegerField(default=0, help_text="최소 전월 실적")
    max_performance_amount = models.PositiveIntegerField(null=True, blank=True, help_text="해당 혜택 상한 구간")
    discount_type = models.CharField(max_length=32, choices=CardPolicy.DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    brand_scope = models.CharField(max_length=32, default="all")
    min_payment_amount = models.PositiveIntegerField(null=True, blank=True, help_text="건당 최소 결제금액")
    monthly_discount_limit = models.PositiveIntegerField(null=True, blank=True, help_text="월간 할인 한도")

    class Meta:
        ordering = ["card_catalog", "fuel_type", "min_performance_amount"]

    def __str__(self):
        return f"{self.card_catalog.card_name} - {self.fuel_type} ({self.min_performance_amount}~)"


class StandardFuelPrice(models.Model):
    """
    알고리즘 계산 시 오차를 없애기 위한 기준 고시 유가 (Opinet API 등을 통해 수집)
    """
    fuel_type = models.CharField(max_length=32)
    price_per_liter = models.DecimalField(max_digits=10, decimal_places=2)
    collected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-collected_at", "fuel_type"]

    def __str__(self):
        return f"{self.fuel_type} - {self.price_per_liter} ({self.collected_at.strftime('%Y-%m-%d')})"


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


class CardIngestionTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "대기 중"
        PROCESSING = "PROCESSING", "수집 중"
        SUCCESS = "SUCCESS", "수집 완료"
        FAILED = "FAILED", "실패"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    query = models.CharField(max_length=255)
    error_message = models.TextField(blank=True, null=True)
    results = models.ManyToManyField(CardCatalog, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Task {self.id} ({self.status}) for '{self.query}'"
