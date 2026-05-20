from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CardCatalog, CardPolicy
from .serializers import (
    CardCatalogSerializer,
    CardDiscoveryQuerySerializer,
    CardFromCatalogSerializer,
    CardPolicySerializer,
)
from .selenium_ingestion import discover_card_benefits


ERROR_MESSAGES = {
    "CARD_POLICY_NOT_FOUND": "카드 정책을 찾을 수 없습니다.",
    "CARD_CATALOG_NOT_FOUND": "카드 카탈로그 후보를 찾을 수 없습니다.",
    "INVALID_CARD_POLICY": "카드 정책 입력값이 올바르지 않습니다.",
    "INVALID_CARD_DISCOVERY_QUERY": "카드 혜택 검색어가 올바르지 않습니다.",
}


def error_response(code, http_status, details=None):
    return Response(
        {
            "code": code,
            "message": ERROR_MESSAGES[code],
            "details": details,
        },
        status=http_status,
    )


class MyCardPolicyListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        policies = CardPolicy.objects.filter(owner=request.user, is_active=True)
        serializer = CardPolicySerializer(policies, many=True)
        return Response({"cards": serializer.data})

    def post(self, request):
        serializer = CardPolicySerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return error_response("INVALID_CARD_POLICY", status.HTTP_400_BAD_REQUEST, serializer.errors)
        policy = serializer.save()
        return Response(CardPolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class MyCardPolicyFromCatalogAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CardFromCatalogSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("INVALID_CARD_POLICY", status.HTTP_400_BAD_REQUEST, serializer.errors)

        catalog = CardCatalog.objects.filter(id=serializer.validated_data["catalog_card_id"]).first()
        if catalog is None:
            return error_response("CARD_CATALOG_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        policy = CardPolicy.objects.create(
            owner=request.user,
            card_name=catalog.card_name,
            issuer_name=catalog.issuer_name,
            discount_type=serializer.validated_data.get("discount_type", catalog.discount_type),
            discount_value=serializer.validated_data.get("discount_value", catalog.discount_value),
            brand_scope=serializer.validated_data.get("brand_scope", catalog.brand_scope),
            min_payment_amount=serializer.validated_data.get("min_payment_amount", catalog.min_payment_amount),
            max_discount_amount=serializer.validated_data.get("max_discount_amount", catalog.max_discount_amount),
            monthly_discount_limit=serializer.validated_data.get(
                "monthly_discount_limit",
                catalog.monthly_discount_limit,
            ),
            monthly_remaining_discount=serializer.validated_data.get(
                "monthly_remaining_discount",
                catalog.monthly_remaining_discount,
            ),
            source_type=CardPolicy.SourceType.SELENIUM,
            verification_status=CardPolicy.VerificationStatus.USER_CONFIRMED,
            card_image_url=catalog.card_image_url,
            source_url=catalog.source_url,
            source_title=catalog.source_title,
            user_memo=serializer.validated_data.get("user_memo", ""),
        )
        return Response(CardPolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class MyCardPolicyDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, card_id):
        policy = CardPolicy.objects.filter(owner=request.user, id=card_id, is_active=True).first()
        if policy is None:
            return error_response("CARD_POLICY_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        serializer = CardPolicySerializer(policy, data=request.data, partial=True, context={"request": request})
        if not serializer.is_valid():
            return error_response("INVALID_CARD_POLICY", status.HTTP_400_BAD_REQUEST, serializer.errors)
        policy = serializer.save()
        return Response(CardPolicySerializer(policy).data)

    def delete(self, request, card_id):
        deleted = CardPolicy.objects.filter(owner=request.user, id=card_id, is_active=True).update(is_active=False)
        if not deleted:
            return error_response("CARD_POLICY_NOT_FOUND", status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CardCatalogListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = CardCatalog.objects.all()
        query = (request.query_params.get("query") or "").strip()
        issuer_name = (request.query_params.get("issuer_name") or "").strip()
        brand_scope = (request.query_params.get("brand_scope") or "").strip()

        if query:
            queryset = queryset.filter(card_name__icontains=query)
        if issuer_name:
            queryset = queryset.filter(issuer_name__icontains=issuer_name)
        if brand_scope:
            queryset = queryset.filter(brand_scope=brand_scope)

        serializer = CardCatalogSerializer(queryset[:50], many=True)
        return Response({"cards": serializer.data})


class CardDiscoveryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CardDiscoveryQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response("INVALID_CARD_DISCOVERY_QUERY", status.HTTP_400_BAD_REQUEST, serializer.errors)

        data = serializer.validated_data
        discovery = discover_card_benefits(
            query=data["query"],
            issuer_name=data.get("issuer_name") or None,
            domain=data.get("domain") or None,
        )
        return Response(
            {
                "candidates": discovery["candidates"],
                "meta": {
                    "source_type": "selenium",
                    "requires_user_confirmation": True,
                    "provider_status": discovery["provider_status"],
                    "allowed_domains": discovery["allowed_domains"],
                },
            }
        )
