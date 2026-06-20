<script setup>
import { reactive, ref } from "vue";
import { Check, Plus } from "@lucide/vue";

import { addVehicle } from "../../api/vehicles";
import VehicleTypePicker from "./VehicleTypePicker.vue";
import {
  VEHICLE_FUEL_LABELS,
  VEHICLE_NAME_MAX_LENGTH,
  buildVehiclePayload,
} from "./vehiclePresentation";

const props = defineProps({
  actionPending: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["changed", "create-start", "create-end"]);

const createForm = reactive({
  name: "",
  vehicle_type: "sedan",
  fuel_type: "gasoline",
  fuel_efficiency_kmpl: 10,
});
const loading = ref(false);
const errorMessage = ref("");
const successMessage = ref("");

const fuelLabels = VEHICLE_FUEL_LABELS;

function readableError(error, fallback) {
  const details = error?.payload?.details;
  if (details && typeof details === "object") {
    const first = Object.values(details).flat()[0];
    if (first) return String(first);
  }
  return error?.payload?.message || error?.message || fallback;
}

function resetCreateForm() {
  createForm.name = "";
  createForm.vehicle_type = "sedan";
  createForm.fuel_type = "gasoline";
  createForm.fuel_efficiency_kmpl = 10;
}

async function handleAddVehicle() {
  if (loading.value || props.actionPending) return;

  errorMessage.value = "";
  successMessage.value = "";
  let payload;
  try {
    payload = buildVehiclePayload(createForm);
  } catch (error) {
    errorMessage.value = error.message;
    return;
  }

  loading.value = true;
  emit("create-start");
  try {
    await addVehicle(payload);
    resetCreateForm();
    successMessage.value = "차량이 등록되었습니다.";
    emit("changed");
  } catch (error) {
    errorMessage.value = readableError(error, "차량 등록에 실패했습니다.");
  } finally {
    loading.value = false;
    emit("create-end");
  }
}
</script>

<template>
  <section class="registerPanel" aria-labelledby="register-title">
    <header class="sectionHeader">
      <div class="sectionTitleGroup">
        <p class="eyebrow">ADD VEHICLE</p>
        <h3 id="register-title">새 차량 등록</h3>
      </div>
      <p>차량을 구분하기 쉬운 이름과 기본 주행 정보를 입력하세요.</p>
    </header>
    <form class="registerForm" @submit.prevent="handleAddVehicle">
      <label>
        <span>차량 이름 <small>{{ createForm.name.trim().length }}/{{ VEHICLE_NAME_MAX_LENGTH }}</small></span>
        <input v-model="createForm.name" :maxlength="VEHICLE_NAME_MAX_LENGTH" placeholder="예: 출퇴근차, 가족차" required />
      </label>
      <fieldset>
        <legend>차량 유형</legend>
        <VehicleTypePicker v-model="createForm.vehicle_type" />
      </fieldset>
      <div class="fuelGrid">
        <label><span>연료</span><select v-model="createForm.fuel_type"><option v-for="(label, value) in fuelLabels" :key="value" :value="value">{{ label }}</option></select></label>
        <label><span>연비 (km/L)</span><input v-model.number="createForm.fuel_efficiency_kmpl" type="number" min="1" max="50" step="0.1" required /></label>
      </div>
      <p class="formHint">입력한 연비는 주유소별 예상 비용 계산에 사용됩니다.</p>
      <p v-if="errorMessage" class="formError" role="alert">{{ errorMessage }}</p>
      <p v-if="successMessage" class="formSuccess" role="status"><Check :size="15" /> {{ successMessage }}</p>
      <button class="primaryAction cardPrimaryButton" type="submit" :disabled="loading || actionPending">
        <Plus :size="18" /> {{ loading ? "등록 중..." : "차량 등록하기" }}
      </button>
    </form>
  </section>
</template>
