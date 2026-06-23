from rest_framework import serializers

from .models import CardBenefitTier, CardCatalog, CardPolicy


def _first_benefit_tier(catalog):
    if catalog is None:
        return None
    prefetched = getattr(catalog, "_prefetched_objects_cache", {}).get("benefit_tiers")
    if prefetched is not None:
        return prefetched[0] if prefetched else None
    return catalog.benefit_tiers.first()


def _policy_benefit(policy):
    return {
        "id": None,
        "fuel_type": "ALL",
        "min_performance_amount": 0,
        "max_performance_amount": None,
        "discount_type": policy.discount_type,
        "discount_value": str(policy.discount_value),
        "brand_scope": policy.brand_scope,
        "min_payment_amount": policy.min_payment_amount,
        "monthly_discount_limit": policy.monthly_discount_limit,
    }


def _policy_uses_catalog_default(policy, tier):
    if policy.discount_value == 0:
        return True
    return (
        policy.discount_type == tier.discount_type
        and policy.discount_value == tier.discount_value
        and policy.brand_scope == tier.brand_scope
        and policy.min_payment_amount == tier.min_payment_amount
        and policy.monthly_discount_limit == tier.monthly_discount_limit
    )


class CardPolicySerializer(serializers.ModelSerializer):
    card_id = serializers.CharField(source="id", read_only=True)
    card_image_url = serializers.URLField(required=False, allow_blank=True)
    card_image_file = serializers.FileField(read_only=True)
    card_image_original_url = serializers.URLField(read_only=True)
    source_url = serializers.URLField(required=False, allow_blank=True)
    source_title = serializers.CharField(required=False, allow_blank=True)
    user_memo = serializers.CharField(required=False, allow_blank=True)
    catalog_benefit_tiers = serializers.SerializerMethodField()
    effective_benefit = serializers.SerializerMethodField()

    class Meta:
        model = CardPolicy
        fields = [
            "card_id",
            "linked_catalog",
            "card_name",
            "issuer_name",
            "discount_type",
            "discount_value",
            "brand_scope",
            "min_payment_amount",
            "max_discount_amount",
            "monthly_discount_limit",
            "monthly_remaining_discount",
            "previous_month_spending",
            "source_type",
            "verification_status",
            "card_image_url",
            "card_image_original_url",
            "card_image_file",
            "source_url",
            "source_title",
            "user_memo",
            "catalog_benefit_tiers",
            "effective_benefit",
        ]
        read_only_fields = ["card_id", "source_type", "verification_status"]

    def get_catalog_benefit_tiers(self, obj):
        if not obj.linked_catalog_id:
            return []
        return CardBenefitTierSerializer(obj.linked_catalog.benefit_tiers.all(), many=True).data

    def get_effective_benefit(self, obj):
        tier = _first_benefit_tier(obj.linked_catalog)
        if tier and _policy_uses_catalog_default(obj, tier):
            return CardBenefitTierSerializer(tier).data
        return _policy_benefit(obj)

    def validate_discount_value(self, value):
        if value < 0:
            raise serializers.ValidationError("discount_value must be greater than or equal to 0.")
        return value

    def validate(self, attrs):
        discount_type = attrs.get("discount_type", getattr(self.instance, "discount_type", None))
        discount_value = attrs.get("discount_value", getattr(self.instance, "discount_value", None))
        if discount_type == CardPolicy.DiscountType.PERCENTAGE and discount_value > 100:
            raise serializers.ValidationError({"discount_value": "percentage discount cannot exceed 100."})
        return attrs

    def create(self, validated_data):
        return CardPolicy.objects.create(
            owner=self.context["request"].user,
            source_type=CardPolicy.SourceType.MANUAL,
            verification_status=CardPolicy.VerificationStatus.USER_CONFIRMED,
            **validated_data,
        )


class CardBenefitTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardBenefitTier
        fields = [
            "id",
            "fuel_type",
            "min_performance_amount",
            "max_performance_amount",
            "discount_type",
            "discount_value",
            "brand_scope",
            "min_payment_amount",
            "monthly_discount_limit",
        ]


class CardCatalogSerializer(serializers.ModelSerializer):
    catalog_card_id = serializers.IntegerField(source="id", read_only=True)
    benefit_tiers = CardBenefitTierSerializer(many=True, read_only=True)
    effective_benefit = serializers.SerializerMethodField()
    card_image_file = serializers.FileField(read_only=True)

    class Meta:
        model = CardCatalog
        fields = [
            "catalog_card_id",
            "card_name",
            "issuer_name",
            "card_image_url",
            "card_image_original_url",
            "card_image_file",
            "source_url",
            "source_title",
            "source_type",
            "verification_status",
            "raw_summary",
            "normalized_data",
            "confidence",
            "collected_at",
            "benefit_tiers",
            "effective_benefit",
        ]

    def get_effective_benefit(self, obj):
        tier = _first_benefit_tier(obj)
        if tier:
            return CardBenefitTierSerializer(tier).data
        return None


class CardFromCatalogSerializer(serializers.Serializer):
    catalog_card_id = serializers.IntegerField()
    discount_type = serializers.ChoiceField(required=False, choices=CardPolicy.DiscountType.choices)
    discount_value = serializers.DecimalField(required=False, max_digits=10, decimal_places=2, min_value=0)
    brand_scope = serializers.CharField(required=False, allow_blank=True, max_length=32)
    min_payment_amount = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    max_discount_amount = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    monthly_discount_limit = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    monthly_remaining_discount = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    previous_month_spending = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    user_memo = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        discount_type = attrs.get("discount_type")
        discount_value = attrs.get("discount_value")
        if discount_type == CardPolicy.DiscountType.PERCENTAGE and discount_value is not None and discount_value > 100:
            raise serializers.ValidationError({"discount_value": "percentage discount cannot exceed 100."})
        return attrs


class CardDiscoveryQuerySerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1, max_length=120)
    issuer_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    domain = serializers.CharField(required=False, allow_blank=True, max_length=255)
