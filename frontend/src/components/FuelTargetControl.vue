<script setup>
import { computed } from "vue";
import {
  VEHICLE_FUEL_LABELS,
  getVehicleFuelPriceUnit
} from "./vehicles/vehiclePresentation";

const props = defineProps({
  isReadOnly: {
    type: Boolean,
    default: false
  }
});

const model = defineModel({ required: true });
const fuelLabels = VEHICLE_FUEL_LABELS;

const calculatedLiters = computed(() => {
  const price = getVehicleFuelPriceUnit(model.value.fuel_type);
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
          <option v-for="(label, value) in fuelLabels" :key="value" :value="value">{{ label }}</option>
        </select>

      </label>
      <label>
        <span>주유 금액 (원)</span>
        <input v-model.number="model.target_amount" type="number" min="5000" max="300000" step="5000" placeholder="예: 50000" />
      </label>

      <label style="grid-column: 1 / -1;">
        <span>이동 경로 기준</span>
        <select v-model="model.travel_mode">
          <option value="round_trip">왕복 (주유소 경유)</option>
          <option value="one_way">편도 (주유소 기준)</option>
        </select>
      </label>

      <div class="estimatedFuelHint">
        <div class="estimatedFuelCopy">
          <span class="estimatedFuelIcon" aria-hidden="true">💡</span>
          <span>
            기준 단가로 계산한 예상 주유량
            <small>주유소마다 실제 주유량은 달라질 수 있습니다.</small>
          </span>
        </div>
        <strong class="estimatedFuelAmount">약 {{ calculatedLiters }} L</strong>
      </div>
    </div>
  </section>
</template>

<style scoped>
.estimatedFuelHint {
  align-items: center;
  background: var(--slate-50);
  border: 1px dashed var(--slate-200);
  border-radius: var(--radius-sm);
  color: var(--slate-600);
  display: flex;
  gap: 12px;
  grid-column: 1 / -1;
  justify-content: space-between;
  margin-top: 4px;
  padding: 10px 12px;
}

.estimatedFuelCopy {
  align-items: flex-start;
  display: flex;
  font-size: 12px;
  font-weight: 800;
  gap: 8px;
  line-height: 1.45;
  min-width: 0;
}

.estimatedFuelCopy small {
  color: var(--slate-400);
  display: block;
  font-size: 11px;
  font-weight: 600;
  margin-top: 2px;
}

.estimatedFuelIcon {
  flex: 0 0 auto;
}

.estimatedFuelAmount {
  color: var(--primary);
  flex: 0 0 auto;
  font-size: 16px;
  font-weight: 900;
  letter-spacing: -0.01em;
  line-height: 1;
  white-space: nowrap;
}

@media (max-width: 520px) {
  .estimatedFuelHint {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
