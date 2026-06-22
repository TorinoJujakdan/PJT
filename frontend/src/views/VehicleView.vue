<script setup>
import { reactive, ref } from "vue";
import { Check, Pencil, Save, Star, Trash2, X } from "@lucide/vue";

import { deleteVehicle, setDefaultVehicle, updateVehicle } from "../api/vehicles";
import VehicleCreateForm from "../components/vehicles/VehicleCreateForm.vue";
import VehicleTypePicker from "../components/vehicles/VehicleTypePicker.vue";
import {
  VEHICLE_NAME_MAX_LENGTH,
  VEHICLE_FUEL_LABELS,
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

const editForm = reactive({
  name: "",
  vehicle_type: "sedan",
  fuel_type: "gasoline",
  fuel_efficiency_kmpl: 10
});
const editingId = ref(null);
const loadingAction = ref(null);
const actionError = ref("");
const editError = ref("");
const successMessage = ref("");

const fuelLabels = VEHICLE_FUEL_LABELS;

function errorMessage(error, fallback) {
  const details = error?.payload?.details;
  if (details && typeof details === "object") {
    const first = Object.values(details).flat()[0];
    if (first) return String(first);
  }
  return error?.payload?.message || error?.message || fallback;
}

function startEdit(vehicle) {
  editingId.value = vehicle.id;
  editError.value = "";
  Object.assign(editForm, {
    name: vehicle.name,
    vehicle_type: vehicle.vehicle_type,
    fuel_type: vehicle.fuel_type,
    fuel_efficiency_kmpl: Number(vehicle.fuel_efficiency_kmpl)
  });
}

function cancelEdit() {
  editingId.value = null;
  editError.value = "";
}

function handleCreateStart() {
  actionError.value = "";
  successMessage.value = "";
  loadingAction.value = "create";
}

function handleCreateEnd() {
  if (loadingAction.value === "create") {
    loadingAction.value = null;
  }
}

async function handleUpdate(vehicleId) {
  if (loadingAction.value) return;

  actionError.value = "";
  editError.value = "";
  successMessage.value = "";
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
  if (loadingAction.value) return;

  actionError.value = "";
  successMessage.value = "";
  loadingAction.value = `default-${vehicleId}`;
  try {
    await setDefaultVehicle(vehicleId);
    successMessage.value = "대표 차량을 변경했습니다.";
    emit("changed");
  } catch (error) {
    actionError.value = errorMessage(error, "대표 차량 설정에 실패했습니다.");
  } finally {
    loadingAction.value = null;
  }
}

async function handleDelete(vehicle) {
  if (loadingAction.value) return;

  if (!confirm(`‘${vehicle.name}’ 차량을 삭제할까요?`)) return;
  actionError.value = "";
  successMessage.value = "";
  loadingAction.value = `delete-${vehicle.id}`;
  try {
    await deleteVehicle(vehicle.id);
    successMessage.value = "차량을 삭제했습니다.";
    emit("changed");
  } catch (error) {
    actionError.value = errorMessage(error, "차량 삭제에 실패했습니다.");
  } finally {
    loadingAction.value = null;
  }
}
</script>

<template>
  <main class="vehicleWorkspace">
    <section class="garagePanel" aria-labelledby="garage-title">
      <header class="sectionHeader">
        <div class="sectionTitleGroup">
          <p class="eyebrow">MY GARAGE</p>
          <div class="titleRow">
            <h3 id="garage-title">등록 차량</h3>
            <span class="countBadge" :aria-label="`등록 차량 ${vehicles.length}대`">{{ vehicles.length }}</span>
          </div>
        </div>
        <p>저장한 차량의 연료와 연비를 한곳에서 관리하고 추천 조건에 바로 적용하세요.</p>
        <p v-if="actionError" class="formError" role="alert">{{ actionError }}</p>
        <p v-if="successMessage" class="formSuccess" role="status"><Check :size="15" /> {{ successMessage }}</p>
      </header>

      <div v-if="!vehicles.length" class="emptyGarage">
        <div class="emptySilhouette">
          <img :src="getVehiclePresentation('sedan').imageUrl" alt="" />
        </div>
        <div>
          <strong>아직 등록한 차량이 없습니다</strong>
          <span>차량을 등록하면 추천 화면에서 연비를 다시 입력하지 않아도 됩니다.</span>
        </div>
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
              <span v-if="vehicle.is_default" class="defaultBadge"><Star :size="13" fill="currentColor" /> 대표 차량</span>
              <img
                :src="getVehiclePresentation(vehicle.vehicle_type).imageUrl"
                :class="getVehiclePresentation(vehicle.vehicle_type).imageClass"
                alt=""
              />
            </div>
            <div class="vehicleInfo">
              <div class="vehicleIdentity">
                <p class="vehicleTypeLabel">{{ getVehiclePresentation(vehicle.vehicle_type).label }}</p>
                <h4>{{ vehicle.name }}</h4>
              </div>
              <dl class="vehicleStats">
                <div>
                  <dt>연료</dt>
                  <dd>{{ fuelLabels[vehicle.fuel_type] || vehicle.fuel_type }}</dd>
                </div>
                <div>
                  <dt>복합 연비</dt>
                  <dd>{{ Number(vehicle.fuel_efficiency_kmpl).toFixed(1) }} <span>km/L</span></dd>
                </div>
              </dl>
            </div>
            <div class="vehicleActions">
              <button
                v-if="!vehicle.is_default"
                type="button"
                :disabled="Boolean(loadingAction)"
                @click="handleSetDefault(vehicle.id)"
              >
                <Check :size="15" /> {{ loadingAction === `default-${vehicle.id}` ? "변경 중..." : "대표로 설정" }}
              </button>
              <button type="button" :disabled="Boolean(loadingAction)" @click="startEdit(vehicle)">
                <Pencil :size="15" /> 수정
              </button>
              <button
                class="danger"
                type="button"
                :disabled="Boolean(loadingAction)"
                @click="handleDelete(vehicle)"
              >
                <Trash2 :size="15" /> {{ loadingAction === `delete-${vehicle.id}` ? "삭제 중..." : "삭제" }}
              </button>
            </div>
          </template>

          <form v-else class="editForm" @submit.prevent="handleUpdate(vehicle.id)">
            <div class="formHeading">
              <strong>차량 정보 수정</strong>
              <button type="button" aria-label="수정 취소" :disabled="Boolean(loadingAction)" @click="cancelEdit"><X :size="17" /></button>
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
            <button class="primaryAction" type="submit" :disabled="Boolean(loadingAction)">
              <Save :size="17" /> {{ loadingAction === `edit-${vehicle.id}` ? "저장 중..." : "수정 내용 저장" }}
            </button>
          </form>
        </article>
      </div>
    </section>

    <VehicleCreateForm
      :action-pending="Boolean(loadingAction)"
      @changed="emit('changed')"
      @create-start="handleCreateStart"
      @create-end="handleCreateEnd"
    />
  </main>
</template>

<style scoped src="../components/vehicles/vehicleWorkspace.css"></style>
