from dataclasses import dataclass
from typing import Any, Optional

from .card_discounts import calculate_card_discount
from .directions import fetch_directions_parallel
from .station_candidates import StationCandidate, get_station_candidates

RECOMMENDATION_PRIORITY_OPTIMAL = "optimal"
RECOMMENDATION_PRIORITY_PRICE = "price"
RECOMMENDATION_PRIORITY_DISTANCE = "distance"

@dataclass(frozen=True)
class FuelPriceRecommendation:
    candidate: StationCandidate
    target_liters: float
    refuel_cost: int
    card_discount_amount: int
    travel_cost: int
    effective_total_cost: int
    estimated_saving: int
    selected_card: Optional[dict[str, Any]]
    reason: str
    distance_source: str = "haversine"
    duration_min: Optional[float] = None
    route_path: Optional[list[dict[str, float]]] = None
    price_collected_at: Optional[Any] = None
    price_source: Optional[str] = None




def calculate_refuel_cost(fuel_price_per_liter, target_liters):
    return round(int(fuel_price_per_liter) * float(target_liters))


def calculate_travel_cost(distance_km, fuel_efficiency_kmpl, fuel_price_per_liter, travel_mode):
    distance_multiplier = 1 if travel_mode == "one_way" else 2
    travel_distance_km = float(distance_km) * distance_multiplier
    travel_fuel_liters = travel_distance_km / float(fuel_efficiency_kmpl)
    return round(travel_fuel_liters * int(fuel_price_per_liter))



def build_recommendation_reason(
    recommendation,
    baseline_cost,
    cheapest_candidate,
    closest_candidate,
    is_winner=False,
):
    station = recommendation.candidate.station
    fuel_price = recommendation.candidate.fuel_price_per_liter
    cost = recommendation.effective_total_cost
    saving = baseline_cost - cost
    prefix = "추천 주유소입니다." if is_winner else "후보 주유소입니다."
    comparison_parts = []

    if cheapest_candidate and cheapest_candidate.station.id != station.id:
        comparison_parts.append(
            f"리터당 최저가 주유소({cheapest_candidate.station.name})보다 "
            f"카드 할인과 이동 비용을 반영한 최종 비용이 유리합니다"
        )
    if closest_candidate and closest_candidate.station.id != station.id:
        comparison_parts.append(
            f"가장 가까운 주유소({closest_candidate.station.name})와 비교해도 "
            f"최종 예상 비용 기준으로 경쟁력이 있습니다"
        )
    if not comparison_parts:
        comparison_parts.append("가격, 거리, 할인 조건을 같은 기준으로 비교했습니다")

    if recommendation.selected_card:
        card = recommendation.selected_card
        return (
            f"{prefix} {station.name}은 {recommendation.target_liters:.2f}L 기준 "
            f"리터당 {fuel_price} KRW, 기본 주유비 {recommendation.refuel_cost} KRW입니다. "
            f"{card['issuer_name']} {card['card_name']} 카드가 "
            f"{recommendation.card_discount_amount} KRW 할인(할인 유형: {card['discount_type']}, "
            f"할인값: {card['discount_value']})을 적용했고, "
            f"왕복 이동 비용은 {recommendation.travel_cost} KRW입니다. "
            f"최종 예상 비용은 {cost} KRW이며 기준 비용 대비 절감액은 {saving} KRW입니다. "
            f"{' '.join(comparison_parts)}."
        )

    return (
        f"{prefix} {station.name}은 {recommendation.target_liters:.2f}L 기준 "
        f"리터당 {fuel_price} KRW, 기본 주유비 {recommendation.refuel_cost} KRW입니다. "
        f"적용 가능한 카드 할인은 없고, 왕복 이동 비용은 {recommendation.travel_cost} KRW입니다. "
        f"최종 예상 비용은 {cost} KRW이며 기준 비용 대비 절감액은 {saving} KRW입니다. "
        f"{' '.join(comparison_parts)}."
    )


def quote_travel_cost_recommendations(
    location,
    radius_km,
    fuel_type,
    target_liters=None,
    target_amount=None,
    fuel_efficiency_kmpl=None,
    travel_mode="round_trip",
    user_cards=None,
    recommendation_priority=RECOMMENDATION_PRIORITY_OPTIMAL,
):
    candidates = get_station_candidates(location=location, radius_km=radius_km, fuel_type=fuel_type)
    if not candidates:
        return []

    # 1단계: 모든 후보에 대해 임시 직선거리 기반 비용 및 임시 baseline 계산
    draft_baseline_cost = min(
        (
            int(target_amount) if target_amount is not None
            else calculate_refuel_cost(candidate.fuel_price_per_liter, target_liters)
        )
        + calculate_travel_cost(
            candidate.distance_km,
            fuel_efficiency_kmpl,
            candidate.fuel_price_per_liter,
            travel_mode,
        )
        for candidate in candidates
    )

    draft_recommendations = []
    for candidate in candidates:
        # target_amount 방식: 각 후보 단가로 독립적으로 리터 계산, 주유비는 목표 금액으로 고정
        if target_amount is not None:
            price = max(candidate.fuel_price_per_liter, 1)  # ZeroDivision 방어
            cand_target_liters = round(target_amount / price, 2)
            refuel_cost = int(target_amount)
        else:
            cand_target_liters = float(target_liters)
            refuel_cost = calculate_refuel_cost(candidate.fuel_price_per_liter, cand_target_liters)

        travel_cost = calculate_travel_cost(
            candidate.distance_km,
            fuel_efficiency_kmpl,
            candidate.fuel_price_per_liter,
            travel_mode,
        )
        card_discount_amount, selected_card = calculate_card_discount(
            candidate,
            refuel_cost,
            cand_target_liters,
            user_cards,
        )
        effective_total_cost = refuel_cost - card_discount_amount + travel_cost
        draft_recommendations.append(
            FuelPriceRecommendation(
                candidate=candidate,
                target_liters=round(float(cand_target_liters), 2),
                refuel_cost=refuel_cost,
                card_discount_amount=card_discount_amount,
                travel_cost=travel_cost,
                effective_total_cost=effective_total_cost,
                estimated_saving=draft_baseline_cost - effective_total_cost,
                selected_card=selected_card,
                reason="",
            )
        )

    # Route every haversine-filtered candidate before final cost/ranking decisions.
    start_lat = float(location["latitude"])
    start_lng = float(location["longitude"])
    direction_results = fetch_directions_parallel(start_lat, start_lng, candidates)

    # 4단계: 도로 경로 결과를 맵핑하여 데이터 최신화 (StationCandidate 및 비용 재산출)
    final_recommendations = []
    for item in draft_recommendations:
        cand = item.candidate
        res = direction_results.get(cand.station.id)

        dist_km = cand.distance_km
        dist_src = "haversine"
        dur_min = None
        route_path = []

        if res and res.get("distance_km") is not None:
            dist_km = res["distance_km"]
            dist_src = res["distance_source"]
            dur_min = res["duration_min"]
            route_path = res.get("route_path") or []

        # 실제 도로 경로에 따른 이동 주유 비용 재계산
        travel_cost = calculate_travel_cost(
            dist_km,
            fuel_efficiency_kmpl,
            cand.fuel_price_per_liter,
            travel_mode,
        )
        effective_total_cost = item.refuel_cost - item.card_discount_amount + travel_cost

        # 직렬화를 위한 시간 및 소스 정보 파싱
        price_coll_at = cand.price_collected_at.isoformat() if cand.price_collected_at else None

        # 5km 이내이며 소스가 opinet인 가격만 live opinet 마킹, 그 외는 database
        is_live = cand.distance_km <= 5.0 and cand.price_source == "opinet"
        price_src = "opinet" if is_live else "database"

        # 불변 객체이므로 업데이트된 속성을 담은 새 StationCandidate 생성
        updated_candidate = StationCandidate(
            station=cand.station,
            distance_km=dist_km,
            fuel_type=cand.fuel_type,
            fuel_price_per_liter=cand.fuel_price_per_liter,
            price_collected_at=cand.price_collected_at,
            price_source=cand.price_source,
        )

        final_recommendations.append(
            FuelPriceRecommendation(
                candidate=updated_candidate,
                target_liters=item.target_liters,
                refuel_cost=item.refuel_cost,
                card_discount_amount=item.card_discount_amount,
                travel_cost=travel_cost,
                effective_total_cost=effective_total_cost,
                estimated_saving=0,  # 다음 단계에서 재계산
                selected_card=item.selected_card,
                reason="",
                distance_source=dist_src,
                duration_min=dur_min,
                route_path=route_path,
                price_collected_at=price_coll_at,
                price_source=price_src,
            )
        )

    # 5단계: 최종 이동비용이 확정된 전체 후보 중 진짜 baseline_cost 도출
    final_baseline_cost = min(
        rec.refuel_cost + rec.travel_cost for rec in final_recommendations
    )

    # 6단계: 최종 정렬 및 각 추천 사유(reason) 빌드
    if recommendation_priority == RECOMMENDATION_PRIORITY_PRICE:
        def sort_key(item):
            return (
                item.candidate.fuel_price_per_liter,
                item.candidate.distance_km,
                item.effective_total_cost,
                item.candidate.station.id,
            )
    elif recommendation_priority == RECOMMENDATION_PRIORITY_DISTANCE:
        def sort_key(item):
            return (
                item.candidate.distance_km,
                item.candidate.fuel_price_per_liter,
                item.effective_total_cost,
                item.candidate.station.id,
            )
    else:
        def sort_key(item):
            return (
                item.effective_total_cost,
                item.candidate.distance_km,
                item.candidate.fuel_price_per_liter,
                item.candidate.station.id,
            )

    sorted_finals = sorted(final_recommendations, key=sort_key)

    cheapest_candidate = min(
        [r.candidate for r in sorted_finals],
        key=lambda item: (item.fuel_price_per_liter, item.distance_km, item.station.id),
    )
    closest_candidate = min(
        [r.candidate for r in sorted_finals],
        key=lambda item: (item.distance_km, item.fuel_price_per_liter, item.station.id),
    )

    recommendations = []
    for index, item in enumerate(sorted_finals):
        saving = final_baseline_cost - item.effective_total_cost

        # 임시 객체를 생성하여 reason을 계산
        temp_rec = FuelPriceRecommendation(
            candidate=item.candidate,
            target_liters=item.target_liters,
            refuel_cost=item.refuel_cost,
            card_discount_amount=item.card_discount_amount,
            travel_cost=item.travel_cost,
            effective_total_cost=item.effective_total_cost,
            estimated_saving=saving,
            selected_card=item.selected_card,
            reason="",
            distance_source=item.distance_source,
            duration_min=item.duration_min,
            route_path=item.route_path,
            price_collected_at=item.price_collected_at,
            price_source=item.price_source,
        )

        reason = build_recommendation_reason(
            temp_rec,
            baseline_cost=final_baseline_cost,
            cheapest_candidate=cheapest_candidate,
            closest_candidate=closest_candidate,
            is_winner=index == 0,
        )

        recommendations.append(
            FuelPriceRecommendation(
                candidate=item.candidate,
                target_liters=item.target_liters,
                refuel_cost=item.refuel_cost,
                card_discount_amount=item.card_discount_amount,
                travel_cost=item.travel_cost,
                effective_total_cost=item.effective_total_cost,
                estimated_saving=saving,
                selected_card=item.selected_card,
                reason=reason,
                distance_source=item.distance_source,
                duration_min=item.duration_min,
                route_path=item.route_path,
                price_collected_at=item.price_collected_at,
                price_source=item.price_source,
            )
        )

    return recommendations



def quote_baseline_without_card(recommendations):
    baseline = min(
        recommendations,
        key=lambda item: (
            item.refuel_cost + item.travel_cost,
            item.candidate.distance_km,
            item.candidate.fuel_price_per_liter,
            item.candidate.station.id,
        ),
    )
    return {
        "station_id": baseline.candidate.station.id,
        "effective_cost_without_card": baseline.refuel_cost + baseline.travel_cost,
    }


def quote_fuel_price_only_recommendations(location, radius_km, fuel_type, target_liters):
    return quote_travel_cost_recommendations(
        location=location,
        radius_km=radius_km,
        fuel_type=fuel_type,
        target_liters=target_liters,
        fuel_efficiency_kmpl=1_000_000,
        travel_mode="one_way",
        recommendation_priority=RECOMMENDATION_PRIORITY_PRICE,
    )
