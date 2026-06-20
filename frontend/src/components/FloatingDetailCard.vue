<script setup>
import { computed } from "vue";
import { CreditCard, Fuel, MapPin, Navigation, X } from "@lucide/vue";

const props = defineProps({
  recommendation: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(["close", "detail"]);

function won(value) {
  return `${Number(value || 0).toLocaleString("ko-KR")}원`;
}

const station = computed(() => props.recommendation?.station || {});
const cost = computed(() => props.recommendation?.cost_breakdown || {});
const card = computed(() => props.recommendation?.selected_card || null);

// 카드 할인이 반영된 실질 리터당 단가 (체감가) 계산
const effectivePricePerLiter = computed(() => {
  const basePrice = station.value.fuel_price_per_liter || 0;
  const discountAmount = cost.value.card_discount_amount || 0;
  const liters = cost.value.target_liters || 1;
  const discountPerLiter = discountAmount / liters;
  return Math.max(0, Math.round(basePrice - discountPerLiter));
});

// 네이버 지도 검색 / 길찾기 연동 링크 생성
const mapSearchUrl = computed(() => {
  if (!station.value.name) return "#";
  const addr = station.value.address || '';
  const isUsableAddress = addr && addr !== '주소 정보 없음';
  const query = isUsableAddress ? `${station.value.name} ${addr}` : station.value.name;
  return `https://map.naver.com/v5/search/${encodeURIComponent(query)}`;
});

const isPastData = computed(() => {
  if (station.value.price_source === "database") return true;
  if (!station.value.price_collected_at) return false;
  const collectedTime = new Date(station.value.price_collected_at).getTime();
  const now = new Date().getTime();
  return (now - collectedTime) > 24 * 60 * 60 * 1000;
});

</script>

<template>
  <div class="floatingDetailCard" role="region" aria-label="선택된 주유소 상세 요약">
    <header class="cardHeader">
      <div class="cardTitle">
        <h3 style="display: flex; align-items: center; flex-wrap: wrap; gap: 6px;">
          {{ station.name }}
          <span v-if="isPastData" class="pastDataBadge" style="background-color: var(--accent); color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700; display: inline-block;">⚠️ DB 가격</span>
        </h3>
        <span>
          <Fuel :size="11" style="display:inline; vertical-align:middle;" /> {{ station.brand }}
          &nbsp;&nbsp;
          <MapPin :size="11" style="display:inline; vertical-align:middle;" /> {{ station.distance_km }} km
          <template v-if="station.duration_min">
            &nbsp;&nbsp;
            <span style="font-size: 11px; color: var(--primary); font-weight: 700;">🚗 {{ Math.round(station.duration_min) }}분 소요</span>
          </template>
        </span>
      </div>
      <button class="closeBtn" type="button" @click="emit('close')" aria-label="상세 정보 닫기">
        <X :size="16" />
      </button>
    </header>

    <div class="priceSection">
      <span class="label">최종 체감가 (리터당)</span>
      <span class="value">{{ won(effectivePricePerLiter) }}</span>
    </div>

    <div class="breakdownSection">
      <div class="breakdownRow">
        <span>기본 리터당 단가</span>
        <span>{{ won(station.fuel_price_per_liter) }}</span>
      </div>
      <div v-if="card" class="breakdownRow">
        <span class="benefit">카드 혜택 ({{ card.card_name }})</span>
        <span class="benefit">-{{ won(cost.card_discount_amount) }}</span>
      </div>
      <div v-else class="breakdownRow">
        <span>카드 혜택</span>
        <span>할인 없음</span>
      </div>
      <div class="breakdownRow">
        <span class="cost">연비 고려 이동 비용</span>
        <span class="cost">+{{ won(cost.travel_cost) }}</span>
      </div>
      <div class="breakdownRow subtotal">
        <span>최종 지출액 (주유비 + 이동)</span>
        <strong>{{ won(cost.effective_total_cost) }}</strong>
      </div>
    </div>

    <div class="actionRow">
      <a :href="mapSearchUrl" target="_blank" rel="noopener noreferrer" class="primaryBtnSmall" style="text-decoration: none;">
        <Navigation :size="15" />
        <span>길찾기 (네이버)</span>
      </a>
      <button class="secondaryBtn" type="button" @click="emit('detail', recommendation)">
        상세 정보
      </button>
    </div>
  </div>
</template>
