<script setup>
import { reactive, ref } from "vue";
import { Check, Pencil, Plus, Save, Star, Trash2, X } from "@lucide/vue";

import { addVehicle, deleteVehicle, setDefaultVehicle, updateVehicle } from "../api/vehicles";
import VehicleTypePicker from "../components/vehicles/VehicleTypePicker.vue";
import {
  VEHICLE_NAME_MAX_LENGTH,
  buildVehiclePayload,
  getVehiclePresentation
} from "../components/vehicles/vehiclePresentation";

defineProps({
  vehicles: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(["changed"]);

const createForm = reactive({
  name: "",
  vehicle_type: "sedan",
  fuel_type: "gasoline",
  fuel_efficiency_kmpl: 10
});
const editForm = reactive({
  name: "",
  vehicle_type: "sedan",
  fuel_type: "gasoline",
  fuel_efficiency_kmpl: 10,
  is_default: false
});
const editingId = ref(null);
const loadingAction = ref(null);
const createError = ref("");
const editError = ref("");
const successMessage = ref("");

const fuelLabels = Object.freeze({
  gasoline: "휘발유",
  diesel: "경유",
  lpg: "LPG",
  premium_gasoline: "고급 휘발유"
});

function errorMessage(error, fallback) {
  const details = error?.payload?.details;
  if (details && typeof details === "object") {
    const first = Object.values(details).flat()[0];
    if (first) return String(first);
  }
  return error?.payload?.message || error?.message || fallback;
}

async function handleAddVehicle() {
  createError.value = "";
  successMessage.value = "";
  let payload;
  try {
    payload = buildVehiclePayload(createForm);
  } catch (error) {
    createError.value = error.message;
    return;
  }

  loadingAction.value = "create";
  try {
    await addVehicle(payload);
    createForm.name = "";
    createForm.vehicle_type = "sedan";
    createForm.fuel_type = "gasoline";
    createForm.fuel_efficiency_kmpl = 10;
    successMessage.value = "차량이 등록되었습니다.";
    emit("changed");
  } catch (error) {
    createError.value = errorMessage(error, "차량 등록에 실패했습니다.");
  } finally {
    loadingAction.value = null;
  }
}

function startEdit(vehicle) {
  editingId.value = vehicle.id;
  editError.value = "";
  Object.assign(editForm, {
    name: vehicle.name,
    vehicle_type: vehicle.vehicle_type,
    fuel_type: vehicle.fuel_type,
    fuel_efficiency_kmpl: Number(vehicle.fuel_efficiency_kmpl),
    is_default: Boolean(vehicle.is_default)
  });
}

function cancelEdit() {
  editingId.value = null;
  editError.value = "";
}

async function handleUpdate(vehicleId) {
  editError.value = "";
  let payload;
  try {
    payload = buildVehiclePayload(editForm);
  } catch (error) {
    editError.value = error.message;
    return;
  }

  loadingAction.value = `edit-${vehicleId}`;
  try {
    await updateVehicle(vehicleId, payload);
    editingId.value = null;
    successMessage.value = "차량 정보가 수정되었습니다.";
    emit("changed");
  } catch (error) {
    editError.value = errorMessage(error, "차량 수정에 실패했습니다.");
  } finally {
    loadingAction.value = null;
  }
}

async function handleSetDefault(vehicleId) {
  loadingAction.value = `default-${vehicleId}`;
  try {
    await setDefaultVehicle(vehicleId);
    successMessage.value = "대표 차량을 변경했습니다.";
    emit("changed");
  } catch (error) {
    createError.value = errorMessage(error, "대표 차량 설정에 실패했습니다.");
  } finally {
    loadingAction.value = null;
  }
}

async function handleDelete(vehicle) {
  if (!confirm(`‘${vehicle.name}’ 차량을 삭제할까요?`)) return;
  loadingAction.value = `delete-${vehicle.id}`;
  try {
    await deleteVehicle(vehicle.id);
    successMessage.value = "차량을 삭제했습니다.";
    emit("changed");
  } catch (error) {
    createError.value = errorMessage(error, "차량 삭제에 실패했습니다.");
  } finally {
    loadingAction.value = null;
  }
}
</script>

<template>
  <main class="vehicleWorkspace">
    <section class="garagePanel" aria-labelledby="garage-title">
      <header class="sectionHeader">
        <div>
          <p class="eyebrow">MY GARAGE</p>
          <h3 id="garage-title">등록 차량 <span>{{ vehicles.length }}</span></h3>
        </div>
        <p>차량 이름과 실루엣으로 여러 차량을 빠르게 구분할 수 있습니다.</p>
      </header>

      <div v-if="!vehicles.length" class="emptyGarage">
        <div class="emptySilhouette">
          <img :src="getVehiclePresentation('sedan').imageUrl" alt="" />
        </div>
        <strong>아직 등록한 차량이 없습니다</strong>
        <span>오른쪽 등록 양식에서 첫 차량을 추가해 보세요.</span>
      </div>

      <div v-else class="vehicleList">
        <article
          v-for="vehicle in vehicles"
          :key="vehicle.id"
          class="vehicleCard"
          :class="{ defaultVehicle: vehicle.is_default }"
        >
          <template v-if="editingId !== vehicle.id">
            <div class="vehicleVisual">
              <span v-if="vehicle.is_default" class="defaultBadge"><Star :size="13" /> 대표 차량</span>
              <img :src="getVehiclePresentation(vehicle.vehicle_type).imageUrl" alt="" />
            </div>
            <div class="vehicleInfo">
              <div>
                <p>{{ getVehiclePresentation(vehicle.vehicle_type).label }}</p>
                <h4>{{ vehicle.name }}</h4>
              </div>
              <dl>
                <div><dt>연료</dt><dd>{{ fuelLabels[vehicle.fuel_type] || vehicle.fuel_type }}</dd></div>
                <div><dt>복합 연비</dt><dd>{{ Number(vehicle.fuel_efficiency_kmpl).toFixed(1) }} km/L</dd></div>
              </dl>
            </div>
            <div class="vehicleActions">
              <button v-if="!vehicle.is_default" type="button" @click="handleSetDefault(vehicle.id)">
                <Check :size="15" /> 대표로 설정
              </button>
              <button type="button" @click="startEdit(vehicle)"><Pencil :size="15" /> 수정</button>
              <button class="danger" type="button" @click="handleDelete(vehicle)">
                <Trash2 :size="15" /> 삭제
              </button>
            </div>
          </template>

          <form v-else class="editForm" @submit.prevent="handleUpdate(vehicle.id)">
            <div class="formHeading">
              <strong>차량 정보 수정</strong>
              <button type="button" aria-label="수정 취소" @click="cancelEdit"><X :size="17" /></button>
            </div>
            <label>
              <span>차량 이름</span>
              <input v-model="editForm.name" :maxlength="VEHICLE_NAME_MAX_LENGTH" required />
            </label>
            <VehicleTypePicker v-model="editForm.vehicle_type" compact />
            <div class="fuelGrid">
              <label><span>연료</span><select v-model="editForm.fuel_type"><option v-for="(label, value) in fuelLabels" :key="value" :value="value">{{ label }}</option></select></label>
              <label><span>연비 (km/L)</span><input v-model.number="editForm.fuel_efficiency_kmpl" type="number" min="1" max="50" step="0.1" required /></label>
            </div>
            <p v-if="editError" class="formError" role="alert">{{ editError }}</p>
            <button class="primaryAction" type="submit" :disabled="loadingAction === `edit-${vehicle.id}`">
              <Save :size="17" /> {{ loadingAction === `edit-${vehicle.id}` ? "저장 중..." : "수정 내용 저장" }}
            </button>
          </form>
        </article>
      </div>
    </section>

    <section class="registerPanel" aria-labelledby="register-title">
      <header class="sectionHeader">
        <div>
          <p class="eyebrow">ADD VEHICLE</p>
          <h3 id="register-title">새 차량 등록</h3>
        </div>
        <p>실제 모델명이 아닌, 알아보기 쉬운 이름을 자유롭게 입력하세요.</p>
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
        <p v-if="createError" class="formError" role="alert">{{ createError }}</p>
        <p v-if="successMessage" class="formSuccess" role="status"><Check :size="15" /> {{ successMessage }}</p>
        <button class="primaryAction" type="submit" :disabled="loadingAction === 'create'">
          <Plus :size="18" /> {{ loadingAction === "create" ? "등록 중..." : "차량 등록하기" }}
        </button>
      </form>
    </section>
  </main>
</template>

<style scoped src="../components/vehicles/vehicleWorkspace.css"></style>
