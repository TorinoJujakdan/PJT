import atexit
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_normalization import save_ai_normalized_candidates
from .gemini_client import normalize_card_fuel_benefit
from .models import CardCatalog, CardIngestionTask, CardPolicy
from .selenium_ingestion import scrape_card_search_candidates
from .serializers import (
    CardCatalogSerializer,
    CardDiscoveryQuerySerializer,
    CardFromCatalogSerializer,
    CardPolicySerializer,
    catalog_requires_manual_benefit_entry,
)

ERROR_MESSAGES = {
    "CARD_POLICY_NOT_FOUND": "카드 정책을 찾을 수 없습니다.",
    "CARD_CATALOG_NOT_FOUND": "카드 카탈로그 후보를 찾을 수 없습니다.",
    "INVALID_CARD_POLICY": "카드 정책 입력값이 올바르지 않습니다.",
    "INVALID_CARD_DISCOVERY_QUERY": "카드 혜택 검색어가 올바르지 않습니다.",
}
MANUAL_BENEFIT_REQUIRED_FIELDS = ("discount_type", "discount_value", "brand_scope")


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
        policies = CardPolicy.objects.filter(owner=request.user, is_active=True).select_related(
            "linked_catalog"
        ).prefetch_related("linked_catalog__benefit_tiers")
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

        catalog = CardCatalog.objects.prefetch_related("benefit_tiers").filter(
            id=serializer.validated_data["catalog_card_id"]
        ).first()
        if catalog is None:
            return error_response("CARD_CATALOG_NOT_FOUND", status.HTTP_404_NOT_FOUND)
        requires_manual_entry = catalog_requires_manual_benefit_entry(catalog)
        if requires_manual_entry and not _has_manual_benefit(serializer.validated_data):
            return error_response(
                "INVALID_CARD_POLICY",
                status.HTTP_400_BAD_REQUEST,
                {
                    "catalog_card_id": "manual benefit fields are required for unverified catalog fuel benefits.",
                    "required_fields": MANUAL_BENEFIT_REQUIRED_FIELDS,
                },
            )

        # CardBenefitTier에서 첫 번째 혜택 구간의 기본값을 가져옵니다.
        default_tier = None if requires_manual_entry else catalog.benefit_tiers.first()
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


def _has_manual_benefit(validated_data):
    return (
        validated_data.get("discount_type") is not None
        and validated_data.get("discount_value") is not None
        and validated_data["discount_value"] > 0
        and bool(validated_data.get("brand_scope"))
    )


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
    """백그라운드 스레드에서 실제 Selenium 수집을 돌리고 DB를 갱신합니다.

    수집 흐름:
    1. Selenium으로 네이버 카드검색 목록 + 각 카드 상세 페이지 방문
       (include_detail=True → min_payment, monthly_limit 원문 확보)
    2. Gemini LLM으로 주유 혜택 섹션을 직접 청킹·추출 → DB 저장
       Gemini 호출 실패 시 task를 FAILED로 기록하며 heuristic fallback 저장은 하지 않습니다.
    """
    close_old_connections()
    try:
        task = CardIngestionTask.objects.get(id=task_id)
        task.status = CardIngestionTask.Status.PROCESSING
        task.save()

        SOURCE_URL = "https://card-search.naver.com/list"

        # 1. Selenium 수집 — 상세 페이지 방문으로 혜택 원문 전체 확보
        candidates = scrape_card_search_candidates(
            limit=10,
            include_detail=True,    # 상세 페이지 방문 → min_payment, monthly_limit 수집
            detail_wait_seconds=1,
        )

        # 2. Gemini LLM normalization and DB storage.
        #    Fail closed on Gemini errors; do not fall back to heuristic Selenium persistence.
        with transaction.atomic():
            saved_cards = save_ai_normalized_candidates(
                candidates,
                source_url=SOURCE_URL,
                normalizer=normalize_card_fuel_benefit,
            )
            # 3. 태스크 결과 매핑 및 완료 처리
            task.results.add(*saved_cards)
            task.status = CardIngestionTask.Status.SUCCESS
            task.save(update_fields=["status"])
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

        from .selenium_ingestion import discover_card_benefits

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
        # IDOR 방지: 현재 사용자가 생성한 태스크만 조회
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
