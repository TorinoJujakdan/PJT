<script setup>
import { computed } from "vue";
const props = defineProps({
  isReadOnly: {
    type: Boolean,
    default: false
  }
});

const model = defineModel({ required: true });

function getFuelPriceUnit(type) {
  if (type === "diesel") return 1500;
  if (type === "lpg") return 1000;
  if (type === "premium_gasoline") return 1850;
  return 1650; // gasoline
}

const calculatedLiters = computed(() => {
  const price = getFuelPriceUnit(model.value.fuel_type);
  const amount = Number(model.value.target_amount) || 0;
  return (amount / price).toFixed(1);
});
</script>

<template>
  <section class="panel">
    <div class="panelHeader">
      <div>
        <p class="eyebrow">Fuel Settings</p>
        <h2>주유 조건 설정</h2>
      </div>
    </div>
    <div class="fieldGrid two">
      <label>
        <span>유종</span>
        <select v-model="model.fuel_type" :disabled="isReadOnly">
          <option value="gasoline">휘발유 (1,650원/L)</option>
          <option value="diesel">경유 (1,500원/L)</option>
          <option value="lpg">LPG (1,000원/L)</option>
          <option value="premium_gasoline">고급 휘발유 (1,850원/L)</option>
        </select>
      </label>
      <label>
        <span>주유 금액 (원)</span>
        <input v-model.number="model.target_amount" type="number" min="5000" max="300000" step="5000" placeholder="예: 50000" />
      </label>
      <label>
        <span>차량 연비 (km/L)</span>
        <input v-model.number="model.fuel_efficiency_kmpl" type="number" min="1" max="50" step="0.1" :disabled="isReadOnly" />
      </label>
      <label>
        <span>이동 경로 기준</span>
        <select v-model="model.travel_mode">
          <option value="round_trip">왕복 (주유소 경유)</option>
          <option value="one_way">편도 (도착지 기준)</option>
        </select>
      </label>

      <!-- Real-time estimated liters information helper -->
      <div style="grid-column: 1 / -1; background: var(--slate-50); border: 1px dashed var(--slate-200); border-radius: var(--radius-sm); padding: 8px 12px; font-size: 12px; font-weight: 700; color: var(--slate-600); display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
        <span>💡 기준 단가 대비 예상 주유량</span>
        <span style="color: var(--primary); font-weight: 800; font-size: 13px;">약 {{ calculatedLiters }} L</span>
      </div>
    </div>
  </section>
</template>
