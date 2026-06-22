from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import atexit

from concurrent.futures import ThreadPoolExecutor
from django.db import close_old_connections
from .models import CardCatalog, CardPolicy, CardIngestionTask
from .serializers import (
    CardCatalogSerializer,
    CardDiscoveryQuerySerializer,
    CardFromCatalogSerializer,
    CardPolicySerializer,
)
from .selenium_ingestion import discover_card_benefits, scrape_card_search_candidates, save_candidates



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

        # CardBenefitTier에서 첫 번째 혜택 구간의 기본값을 가져옵니다.
        default_tier = catalog.benefit_tiers.first()
        default_discount_type = default_tier.discount_type if default_tier else CardPolicy.DiscountType.PER_LITER
        default_discount_value = default_tier.discount_value if default_tier else 0
        default_brand_scope = default_tier.brand_scope if default_tier else "all"
        default_min_payment = default_tier.min_payment_amount if default_tier else None
        default_monthly_limit = default_tier.monthly_discount_limit if default_tier else None

        policy = CardPolicy.objects.create(
            owner=request.user,
            linked_catalog=catalog,
            card_name=catalog.card_name,
            issuer_name=catalog.issuer_name,
            discount_type=serializer.validated_data.get("discount_type", default_discount_type),
            discount_value=serializer.validated_data.get("discount_value", default_discount_value),
            brand_scope=serializer.validated_data.get("brand_scope", default_brand_scope),
            min_payment_amount=serializer.validated_data.get("min_payment_amount", default_min_payment),
            max_discount_amount=serializer.validated_data.get("max_discount_amount", None),
            monthly_discount_limit=serializer.validated_data.get(
                "monthly_discount_limit",
                default_monthly_limit,
            ),
            monthly_remaining_discount=serializer.validated_data.get(
                "monthly_remaining_discount",
                None,
            ),
            previous_month_spending=serializer.validated_data.get("previous_month_spending", None),
            source_type=CardPolicy.SourceType.CATALOG,
            verification_status=CardPolicy.VerificationStatus.USER_CONFIRMED,
            card_image_url=catalog.card_image_url,
            card_image_original_url=catalog.card_image_original_url,
            card_image_file=catalog.card_image_file,
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
        queryset = CardCatalog.objects.prefetch_related("benefit_tiers").all()
        query = (request.query_params.get("query") or "").strip()
        issuer_name = (request.query_params.get("issuer_name") or "").strip()

        if query:
            queryset = queryset.filter(card_name__icontains=query)
        if issuer_name:
            queryset = queryset.filter(issuer_name__icontains=issuer_name)

        serializer = CardCatalogSerializer(queryset[:50], many=True)
        return Response({"cards": serializer.data})


# 전역 백그라운드 스레드 풀 생성 (가벼운 동시성 유지)
executor = ThreadPoolExecutor(max_workers=2)
atexit.register(executor.shutdown, wait=False)

def run_background_ingestion(task_id, query):
    """백그라운드 스레드에서 실제 Selenium 수집을 돌리고 DB를 갱신합니다."""
    close_old_connections()
    try:
        task = CardIngestionTask.objects.get(id=task_id)
        task.status = CardIngestionTask.Status.PROCESSING
        task.save()

        # 1. 셀레니움 수집 구동 (최대 10개 수집 제한으로 빠르게 응답)
        candidates = scrape_card_search_candidates(limit=10)

        # 2. 자동 검증 및 DB 저장
        saved_cards = save_candidates(candidates, "https://card-search.naver.com/list")

        # 3. 태스크 결과 매핑 및 완료 처리
        task.results.add(*saved_cards)
        task.status = CardIngestionTask.Status.SUCCESS
    except Exception as e:
        try:
            task = CardIngestionTask.objects.get(id=task_id)
            task.status = CardIngestionTask.Status.FAILED
            task.error_message = str(e)
            task.save()
        except Exception:
            pass
    finally:
        close_old_connections()


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

    def post(self, request):
        query = request.data.get("query", "").strip()
        if not query:
            return Response(
                {
                    "code": "MISSING_QUERY",
                    "message": "검색어(query)가 필요합니다."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. 태스크 레코드 생성
        task = CardIngestionTask.objects.create(query=query, owner=request.user)

        # 2. 스레드 풀에 작업 위임 (즉시 리턴)
        executor.submit(run_background_ingestion, task.id, query)

        return Response(
            {
                "task_id": task.id,
                "status": task.status,
                "message": "백그라운드 카드 수집이 시작되었습니다."
            },
            status=status.HTTP_202_ACCEPTED
        )



class CardDiscoveryTaskStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        from django.shortcuts import get_object_or_404
        # IDOR 방지: 현재 유저의 세션에서 생성된 태스크만 조회
        # TODO: CardIngestionTask에 owner 필드를 추가하여 완전한 권한 검증 필요
        task = get_object_or_404(CardIngestionTask, id=task_id, owner=request.user)
        response_data = {
            "task_id": task.id,
            "status": task.status,
            "error_message": task.error_message,
            "candidates": []
        }

        if task.status == CardIngestionTask.Status.SUCCESS:
            cards = task.results.all()
            response_data["candidates"] = CardCatalogSerializer(cards, many=True).data

        return Response(response_data)
