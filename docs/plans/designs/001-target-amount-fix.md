# SmartFuel 최종 지출액 계산 버그 수정 (target_amount 기반 계산)

## 배경

사용자가 주유 조건을 "50,000원 어치 주유"로 설정하고 맞춤 추천 검색을 실행하면,
우측 하단 카드에 표시되는 **최종 지출액(주유비 + 이동)이 55,612원**으로 나타난다.
이는 의도한 금액(50,000원 + 이동비용)보다 크게 과다 계산된 값이다.

## 근본 원인

### 버그 재현 경로

```
1. [frontend] FuelTargetControl.vue
   사용자 입력: target_amount = 50,000원

2. [frontend] useSmartFuelDashboard.js L122-123
   priceUnit = getVehicleFuelPriceUnit("gasoline")  → 하드코딩 1,650원
   calculatedLiters = 50,000 / 1,650 = 30.30L

3. [frontend → backend] API 요청
   { target_liters: 30.30, ... }

4. [backend] services.py - calculate_refuel_cost()
   refuel_cost = 1,999원 × 30.30L = 60,570원  ← 5만원이 아님!

5. [backend] effective_total_cost
   = 60,570 - 6,057(카드할인) + 1,099(이동) = 55,612원
```

### 핵심 불일치

- 프론트는 **하드코딩 기준가(1,650원)**로 리터를 계산
- 백엔드는 **실제 주유소 단가(1,999원)**로 주유비를 다시 계산
- 결과적으로 "5만원치 주유" 조건이 "6만원치 주유"로 둔갑

## 선택된 접근법: Approach C (structural)

> 백엔드에서 `target_amount` 파라미터를 새로 지원하고,
> 각 후보 주유소별로 `target_liters = target_amount / candidate.fuel_price_per_liter`를
> 독립적으로 계산한다.

### 왜 Approach C인가

- **Approach A**: target_amount를 단순 지원하지만 1위 주유소 기준으로만 리터 계산
- **Approach B (tactical)**: API 2회 호출, 1위 주유소만 정확
- **Approach C**: 모든 후보 주유소가 각자의 단가로 정확히 계산 → 비교 의미 극대화

### 수정 후 예상 계산

```
주유 금액: 50,000원, 주유소 단가: 1,999원/L

target_liters (per candidate) = 50,000 / 1,999 = 25.01L
refuel_cost = 50,000원 (고정)
카드 할인 = 25.01L 기준으로 정확히 계산
이동비용 = +1,099원

최종 지출액 = 50,000 - 카드할인 + 1,099원
```

---

## 제안 변경 사항

### Backend

---

#### [MODIFY] serializers.py

`RecommendationQuoteRequestSerializer`에 `target_amount` 필드 추가,
`target_liters`를 optional로 변경, cross-field 검증 추가.

```python
target_liters = serializers.FloatField(min_value=1, max_value=150, required=False, allow_null=True)
target_amount = serializers.IntegerField(min_value=1000, max_value=3_000_000, required=False, allow_null=True)

def validate(self, attrs):
    if not attrs.get('target_liters') and not attrs.get('target_amount'):
        raise serializers.ValidationError(
            "target_liters 또는 target_amount 중 하나는 필수입니다."
        )
    return attrs
```

---

#### [MODIFY] services.py

`quote_travel_cost_recommendations()` 시그니처 및 내부 루프 변경.

```python
def quote_travel_cost_recommendations(
    location, radius_km, fuel_type,
    target_liters=None,   # 기존 (L 직접 지정)
    target_amount=None,   # 신규 (원 기준)
    fuel_efficiency_kmpl, travel_mode,
    user_cards=None,
    recommendation_priority=RECOMMENDATION_PRIORITY_OPTIMAL,
):
    ...
    for candidate in candidates:
        # 후보별 target_liters 계산
        if target_amount is not None:
            price = max(candidate.fuel_price_per_liter, 1)  # ZeroDivision 방어
            cand_target_liters = round(target_amount / price, 2)
            refuel_cost = int(target_amount)  # 항상 사용자 입력 금액으로 고정
        else:
            cand_target_liters = float(target_liters)
            refuel_cost = calculate_refuel_cost(candidate.fuel_price_per_liter, cand_target_liters)
        
        travel_cost = calculate_travel_cost(...)
        card_discount_amount, selected_card = calculate_card_discount(
            candidate, refuel_cost, cand_target_liters, user_cards
        )
        effective_total_cost = refuel_cost - card_discount_amount + travel_cost
```

---

#### [MODIFY] views.py

`quote_travel_cost_recommendations()` 호출 시 `target_amount` 전달.

```python
recommendations = quote_travel_cost_recommendations(
    ...
    target_liters=data.get("target_liters"),
    target_amount=data.get("target_amount"),
    ...
)
```

---

### Frontend

---

#### [MODIFY] useSmartFuelDashboard.js

API 요청 페이로드에서 `target_liters` 계산 제거, `target_amount` 직접 전달.

```js
// 삭제할 코드
const priceUnit = getVehicleFuelPriceUnit(fuel.fuel_type);
const calculatedLiters = Number((fuel.target_amount / priceUnit).toFixed(2));

// 변경 후 request 객체
const request = {
  location: { ... },
  fuel_type: fuel.fuel_type,
  target_amount: fuel.target_amount,  // 원 그대로 전달
  // target_liters: 제거
  travel_mode: fuel.travel_mode,
  ...
};
```

---

#### [MODIFY] FuelTargetControl.vue

힌트 텍스트 레이블 업데이트 (Tier 2 권장사항).

```html
<!-- 기존 -->
💡 기준 단가 대비 예상 주유량

<!-- 변경 후 -->
💡 기준 단가 대비 예상 주유량 (주유소마다 다를 수 있음)
```

---

## 검증 계획

### 자동 테스트

```bash
# 기존 target_liters 기반 테스트 (하위호환 검증)
python manage.py test stations.tests

# 신규 target_amount 파라미터 테스트
python manage.py test stations.tests_additions
```

### 수동 검증

1. 휘발유 50,000원, 왕복 조건으로 검색
2. 최종 지출액 = "50,000원 - 카드할인 + 이동비용" 확인
3. 상세 카드의 "원가 기준 주유비"가 50,000원에 가깝게 표시되는지 확인
4. 여러 후보 주유소별 target_liters가 각 단가에 맞게 다르게 계산되는지 확인

---

## 주의사항

- `target_liters` 파라미터는 optional로 유지 (하위 호환성)
- `fuel_price_per_liter = 0` 방어 코드 필수 (DB에서 null 제외되어 있으나 추가 안전망)
- 프론트의 `getVehicleFuelPriceUnit` 함수는 힌트 표시에만 사용, API 요청에서 제거
