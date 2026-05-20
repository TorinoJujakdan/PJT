<script setup>
defineProps({
  candidates: {
    type: Array,
    default: () => []
  },
  selectedStationId: {
    type: [Number, String],
    default: null
  }
});

const emit = defineEmits(["select"]);

function won(value) {
  return `${Number(value).toLocaleString("ko-KR")}원`;
}
</script>

<template>
  <section class="panel">
    <div class="panelHeader">
      <div>
        <p class="eyebrow">Candidates</p>
        <h2>비교 후보</h2>
      </div>
    </div>
    <div class="candidateTable">
      <div class="candidateRow header">
        <span>주유소</span>
        <span>거리</span>
        <span>리터당</span>
        <span>최종 비용</span>
      </div>
      <button
        v-for="candidate in candidates"
        :key="candidate.station.station_id"
        class="candidateRow selectable"
        :class="{ active: candidate.station.station_id === selectedStationId }"
        type="button"
        @click="emit('select', candidate.station.station_id)"
      >
        <span>{{ candidate.station.name }}</span>
        <span>{{ candidate.station.distance_km }} km</span>
        <span>{{ won(candidate.station.fuel_price_per_liter) }}</span>
        <strong>{{ won(candidate.cost_breakdown.effective_total_cost) }}</strong>
      </button>
    </div>
  </section>
</template>
