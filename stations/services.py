import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_recommendations(user_lat, user_lng, target_amount, stations, user):
    recommendations = []
    car_efficiency = float(user.car_efficiency) if user.is_authenticated else 10.0 # Default 10km/L
    user_cards = user.cards.all() if user.is_authenticated else []

    for station in stations:
        # 1. 1차 필터링: Haversine 거리 계산
        distance_km = haversine(user_lat, user_lng, float(station.latitude), float(station.longitude))
        if distance_km > 15.0: # 15km 이상은 후보에서 제외
            continue

        # 2. 이동 비용 계산
        # 주행 소모 연료량(L) = 거리 / 연비
        consumed_fuel = distance_km / car_efficiency
        driving_cost = consumed_fuel * station.gasoline_price

        # 3. 주유량 및 카드 할인 계산
        # 사용자가 목표 금액만큼 주유할 때 들어가는 기름 양(L)
        liters_to_refuel = target_amount / station.gasoline_price if station.gasoline_price > 0 else 0
        
        best_discount = 0
        # 보유 카드 중 가장 할인율이 높은 카드 탐색
        for card in user_cards:
            # 타겟 브랜드가 지정되어 있고, 현재 주유소 브랜드와 다르면 패스
            if card.target_brand and card.target_brand != station.brand:
                continue
            
            discount = 0
            if card.discount_type == 'FIXED':
                # 리터당 할인 (원)
                discount = liters_to_refuel * float(card.discount_amount)
            elif card.discount_type == 'PERCENT':
                # 총 결제액 퍼센트 할인
                discount = target_amount * (float(card.discount_amount) / 100.0)
            
            if discount > best_discount:
                best_discount = discount

        # 4. 최종 결과 산출
        final_price = target_amount - best_discount
        # 총 절약 금액 = (카드 할인액) - (주행 비용)
        saved_amount = best_discount - driving_cost

        # 내비게이션 URL (Tmap 예시)
        nav_url = f"tmap://search?name={station.name}&x={station.longitude}&y={station.latitude}"

        recommendations.append({
            "station_id": station.id,
            "name": station.name,
            "brand": station.brand,
            "original_price": int(target_amount),
            "final_price": int(final_price),
            "saved_amount": int(saved_amount),
            "distance_km": round(distance_km, 2),
            "navigation_url": nav_url
        })

    # 절약 금액이 가장 큰 순서대로 정렬
    recommendations.sort(key=lambda x: x['saved_amount'], reverse=True)
    return recommendations
