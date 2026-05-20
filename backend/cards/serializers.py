from rest_framework import serializers

from .models import CardCatalog, CardPolicy


class CardPolicySerializer(serializers.ModelSerializer):
    card_id = serializers.CharField(source="id", read_only=True)
    card_image_url = serializers.URLField(required=False, allow_blank=True)
    source_url = serializers.URLField(required=False, allow_blank=True)
    source_title = serializers.CharField(required=False, allow_blank=True)
    user_memo = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CardPolicy
        fields = [
            "card_id",
            "card_name",
            "issuer_name",
            "discount_type",
            "discount_value",
            "brand_scope",
            "min_payment_amount",
            "max_discount_amount",
            "monthly_discount_limit",
            "monthly_remaining_discount",
            "source_type",
            "verification_status",
            "card_image_url",
            "source_url",
            "source_title",
            "user_memo",
        ]
        read_only_fields = ["card_id", "source_type", "verification_status"]

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


class CardCatalogSerializer(serializers.ModelSerializer):
    catalog_card_id = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = CardCatalog
        fields = [
            "catalog_card_id",
            "card_name",
            "issuer_name",
            "discount_type",
            "discount_value",
            "brand_scope",
            "min_payment_amount",
            "max_discount_amount",
            "monthly_discount_limit",
            "monthly_remaining_discount",
            "card_image_url",
            "source_url",
            "source_title",
            "source_type",
            "verification_status",
            "raw_summary",
            "confidence",
            "collected_at",
        ]


class CardFromCatalogSerializer(serializers.Serializer):
    catalog_card_id = serializers.IntegerField()
    discount_type = serializers.ChoiceField(required=False, choices=CardPolicy.DiscountType.choices)
    discount_value = serializers.DecimalField(required=False, max_digits=10, decimal_places=2, min_value=0)
    brand_scope = serializers.CharField(required=False, allow_blank=True, max_length=32)
    min_payment_amount = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    max_discount_amount = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    monthly_discount_limit = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    monthly_remaining_discount = serializers.IntegerField(required=False, allow_null=True, min_value=0)
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
