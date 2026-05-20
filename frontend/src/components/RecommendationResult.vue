<script setup>
import { BadgeCheck, CreditCard, Fuel, MapPin } from "@lucide/vue";
import CostBreakdown from "./CostBreakdown.vue";

defineProps({
  recommendation: {
    type: Object,
    required: true
  }
});

function won(value) {
  return `${Number(value).toLocaleString("ko-KR")}원`;
}
</script>

<template>
  <section class="resultSurface">
    <div class="resultTop">
      <div>
        <p class="eyebrow">Recommendation</p>
        <h1>{{ recommendation.station.name }}</h1>
        <div class="stationMeta">
          <span><Fuel :size="16" /> {{ recommendation.station.brand }}</span>
          <span><MapPin :size="16" /> {{ recommendation.station.distance_km }} km</span>
        </div>
      </div>
      <div class="scoreBox">
        <span>최종 예상 비용</span>
        <strong>{{ won(recommendation.cost_breakdown.effective_total_cost) }}</strong>
      </div>
    </div>

    <CostBreakdown :cost="recommendation.cost_breakdown" />

    <div v-if="recommendation.selected_card" class="selectedCard">
      <div class="cardImage" aria-label="카드 이미지">
        <img
          v-if="recommendation.selected_card.card_image_url"
          :src="recommendation.selected_card.card_image_url"
          :alt="recommendation.selected_card.card_name"
        />
        <CreditCard v-else :size="30" />
      </div>
      <div>
        <p class="eyebrow">Selected Card</p>
        <h3>{{ recommendation.selected_card.issuer_name }} {{ recommendation.selected_card.card_name }}</h3>
        <p>{{ won(recommendation.selected_card.calculated_discount_amount) }} 할인 적용</p>
      </div>
      <BadgeCheck class="verifiedIcon" :size="22" />
    </div>

    <p class="reason">{{ recommendation.reason }}</p>
  </section>
</template>
