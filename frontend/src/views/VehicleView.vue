<script setup>
import { reactive, ref } from "vue";
import { Car, CheckCircle2, Pencil, Plus, Save, Trash2, X } from "@lucide/vue";
import { addVehicle, deleteVehicle, setDefaultVehicle, updateVehicle } from "../api/vehicles";

const props = defineProps({
  vehicles: {
    type: Array,
    default: () => []
  },
  vehicle: {
    type: Object,
    default: null
  }
});
const emit = defineEmits(["saved", "changed"]);

const form = reactive({
  fuel_type: "gasoline",
  fuel_efficiency_kmpl: 10
});
const loading = ref(false);
const error = ref(null);
const saved = ref(false);
const editingId = ref(null);
const editForm = reactive({
  fuel_type: "gasoline",
  fuel_efficiency_kmpl: 10,
  is_default: false
});
const editError = ref(null);
const editLoading = ref(false);

function validateForm() {
  if (!form.fuel_type || !form.fuel_efficiency_kmpl) {
    return "연료 타입과 연비를 모두 입력해 주세요.";
  }

  if (form.fuel_efficiency_kmpl < 1 || form.fuel_efficiency_kmpl > 50) {
    return "연비는 1.0km/L 이상 50.0km/L 이하로 입력해 주세요.";
  }

  return null;
}

async function handleAddVehicle() {
  const validationMessage = validateForm();
  if (validationMessage) {
    error.value = { message: validationMessage };
    saved.value = false;
    return;
  }

  loading.value = true;
  error.value = null;
  saved.value = false;
  try {
    await addVehicle({
      fuel_type: form.fuel_type,
      fuel_efficiency_kmpl: Number(form.fuel_efficiency_kmpl)
    });
    saved.value = true;
    form.fuel_efficiency_kmpl = 10;
    emit("changed");
    emit("saved");
  } catch (err) {
    error.value = err.payload || { message: err.message };
  } finally {
    loading.value = false;
  }
}

async function handleSetDefault(id) {
  try {
    await setDefaultVehicle(id);
    emit("changed");
  } catch (err) {
    alert(err.message || "대표 차량 설정에 실패했습니다.");
  }
}

async function handleDelete(id) {
  if (!confirm("이 차량을 정말 삭제하시겠습니까?")) return;
  try {
    await deleteVehicle(id);
    emit("changed");
  } catch (err) {
    alert(err.message || "차량 삭제에 실패했습니다.");
  }
}

function startEdit(vehicle) {
  editingId.value = vehicle.id;
  editError.value = null;
  Object.assign(editForm, {
    fuel_type: vehicle.fuel_type,
    fuel_efficiency_kmpl: Number(vehicle.fuel_efficiency_kmpl),
    is_default: Boolean(vehicle.is_default)
  });
}

function cancelEdit() {
  editingId.value = null;
  editError.value = null;
}

async function handleUpdateVehicle(id) {
  const validationMessage = validateFormFor(editForm);
  if (validationMessage) {
    editError.value = { message: validationMessage };
    return;
  }

  editLoading.value = true;
  editError.value = null;
  try {
    await updateVehicle(id, {
      fuel_type: editForm.fuel_type,
      fuel_efficiency_kmpl: Number(editForm.fuel_efficiency_kmpl),
      is_default: editForm.is_default
    });
    editingId.value = null;
    emit("changed");
  } catch (err) {
    editError.value = err.payload || { message: err.message };
  } finally {
    editLoading.value = false;
  }
}

function validateFormFor(target) {
  if (!target.fuel_type || !target.fuel_efficiency_kmpl) {
    return "연료 타입과 연비를 모두 입력해 주세요.";
  }

  if (target.fuel_efficiency_kmpl < 1 || target.fuel_efficiency_kmpl > 50) {
    return "연비는 1.0km/L 이상 50.0km/L 이하로 입력해 주세요.";
  }

  return null;
}

function getFuelTypeName(type) {
  const names = {
    gasoline: "휘발유",
    diesel: "경유",
    lpg: "LPG",
    premium_gasoline: "고급 휘발유"
  };
  return names[type] || type;
}
</script>

<template>
  <main class="workspace gridLayout">
    <!-- Left: Vehicle List Dashboard -->
    <section class="panel listPanel">
      <div class="panelHeader">
        <div>
          <p class="eyebrow">My Garage</p>
          <h2>내 등록 차량 목록 ({{ vehicles.length }})</h2>
        </div>
      </div>

      <div class="vehiclesContainer">
        <div v-if="vehicles.length === 0" class="noVehicles">
          <Car :size="48" class="emptyIcon" />
          <p>등록된 차량이 없습니다.</p>
          <span>오른쪽 폼에서 차량을 추가해 보세요!</span>
        </div>

        <div v-else class="vehicleCardsGrid">
          <div
            v-for="v in vehicles"
            :key="v.id"
            class="vehicleCard"
            :class="{ isDefault: v.is_default }"
          >
            <div class="cardMain">
              <div class="cardBadge" :class="v.fuel_type">
                {{ getFuelTypeName(v.fuel_type) }}
              </div>
              <div class="efficiency">
                <span class="num">{{ Number(v.fuel_efficiency_kmpl).toFixed(1) }}</span>
                <span class="unit">km/L</span>
              </div>
            </div>

            <form v-if="editingId === v.id" class="inlineEditForm" @submit.prevent="handleUpdateVehicle(v.id)">
              <label>
                <span>연료 타입</span>
                <select v-model="editForm.fuel_type" required>
                  <option value="gasoline">휘발유</option>
                  <option value="diesel">경유</option>
                  <option value="lpg">LPG</option>
                  <option value="premium_gasoline">고급 휘발유</option>
                </select>
              </label>
              <label>
                <span>연비(km/L)</span>
                <input v-model.number="editForm.fuel_efficiency_kmpl" type="number" min="1" max="50" step="0.1" required />
              </label>
              <label class="checkboxRow">
                <input v-model="editForm.is_default" type="checkbox" />
                <span>대표 차량으로 설정</span>
              </label>
              <div v-if="editError" class="errorPanel compact">
                <strong>{{ editError.code || "UPDATE_FAILED" }}</strong>
                <span>{{ editError.message }}</span>
              </div>
              <div class="inlineEditActions">
                <button class="actionBtn setBtn" type="submit" :disabled="editLoading">
                  <Save :size="16" />
                  <span>{{ editLoading ? "저장 중" : "저장" }}</span>
                </button>
                <button class="actionBtn deleteBtn" type="button" :disabled="editLoading" @click="cancelEdit">
                  <X :size="16" />
                  <span>취소</span>
                </button>
              </div>
            </form>

            <div class="cardActions">
              <button
                v-if="!v.is_default"
                class="actionBtn setBtn"
                type="button"
                title="대표 차량으로 설정"
                @click="handleSetDefault(v.id)"
              >
                <CheckCircle2 :size="16" />
                <span>대표설정</span>
              </button>
              <div v-else class="defaultLabel">
                <CheckCircle2 :size="16" />
                <span>대표 차량</span>
              </div>

              <button
                class="actionBtn setBtn"
                type="button"
                title="차량 수정"
                @click="startEdit(v)"
              >
                <Pencil :size="16" />
                <span>수정</span>
              </button>

              <button
                class="actionBtn deleteBtn"
                type="button"
                title="차량 삭제"
                @click="handleDelete(v.id)"
              >
                <Trash2 :size="16" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Right: Add Vehicle Form -->
    <section class="panel formPanel">
      <div class="panelHeader">
        <div>
          <p class="eyebrow">Add Vehicle</p>
          <h2>신규 차량 등록</h2>
        </div>
      </div>
      <form class="fieldGrid" @submit.prevent="handleAddVehicle">
        <label>
          <span>연료 타입</span>
          <select v-model="form.fuel_type" required>
            <option value="gasoline">휘발유</option>
            <option value="diesel">경유</option>
            <option value="lpg">LPG</option>
            <option value="premium_gasoline">고급 휘발유</option>
          </select>
        </label>
        <label>
          <span>연비(km/L)</span>
          <input v-model.number="form.fuel_efficiency_kmpl" type="number" min="1" max="50" step="0.1" required />
        </label>
        
        <div v-if="error" class="errorPanel compact">
          <strong>{{ error.code || "SAVE_FAILED" }}</strong>
          <span>{{ error.message }}</span>
        </div>
        
        <p v-if="saved" class="successText">차량이 성공적으로 등록되었습니다.</p>
        
        <button class="primaryButton fullWidth" type="submit" :disabled="loading">
          <Plus :size="18" />
          <span>{{ loading ? "등록 중" : "차량 추가 등록" }}</span>
        </button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.gridLayout {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 24px;
  align-items: start;
}
@media (max-width: 900px) {
  .gridLayout {
    grid-template-columns: 1fr;
  }
}

.vehiclesContainer {
  margin-top: 12px;
}
.noVehicles {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  background: rgba(255, 255, 255, 0.02);
  border: 1.5px dashed rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  text-align: center;
}
.emptyIcon {
  color: var(--slate-500);
  opacity: 0.5;
  margin-bottom: 16px;
}
.noVehicles p {
  font-size: 15px;
  font-weight: 700;
  color: var(--slate-300);
}
.noVehicles span {
  font-size: 12px;
  color: var(--slate-400);
  margin-top: 4px;
}

.vehicleCardsGrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.vehicleCard {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 16px;
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.05);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.vehicleCard:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.05);
}
.vehicleCard.isDefault {
  border-color: var(--primary);
  background: rgba(0, 229, 255, 0.02);
  box-shadow: 0 0 16px rgba(0, 229, 255, 0.12), inset 0 1px 1px rgba(255,255,255,0.1);
}

.cardMain {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.cardBadge {
  font-size: 11px;
  font-weight: 800;
  padding: 4px 8px;
  border-radius: 6px;
  text-transform: uppercase;
}
.cardBadge.gasoline {
  background: rgba(255, 171, 0, 0.15);
  color: #ffab00;
  border: 1px solid rgba(255, 171, 0, 0.25);
}
.cardBadge.premium_gasoline {
  background: rgba(255, 86, 48, 0.15);
  color: #ff5630;
  border: 1px solid rgba(255, 86, 48, 0.25);
}
.cardBadge.diesel {
  background: rgba(0, 184, 217, 0.15);
  color: #00b8d9;
  border: 1px solid rgba(0, 184, 217, 0.25);
}
.cardBadge.lpg {
  background: rgba(54, 179, 126, 0.15);
  color: #36b37e;
  border: 1px solid rgba(54, 179, 126, 0.25);
}

.efficiency {
  display: flex;
  align-items: baseline;
  gap: 2px;
}
.efficiency .num {
  font-size: 20px;
  font-weight: 900;
  color: var(--secondary);
}
.efficiency .unit {
  font-size: 11px;
  color: var(--slate-400);
  font-weight: 700;
}

.cardActions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 12px;
  gap: 8px;
  flex-wrap: wrap;
}

.inlineEditForm {
  display: grid;
  gap: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 12px;
}

.inlineEditForm label {
  display: grid;
  gap: 5px;
}

.inlineEditForm label span {
  color: var(--slate-400);
  font-size: 11px;
  font-weight: 800;
}

.checkboxRow {
  align-items: center;
  display: flex !important;
  gap: 8px;
}

.checkboxRow input {
  width: auto;
}

.inlineEditActions {
  display: flex;
  gap: 8px;
}

.actionBtn {
  background: transparent;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  font-weight: 700;
  border-radius: 6px;
  transition: all 0.2s;
}
.setBtn {
  color: var(--slate-400);
}
.setBtn:hover {
  color: var(--primary);
}

.defaultLabel {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  font-weight: 800;
  color: var(--primary);
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.3);
}

.deleteBtn {
  color: var(--slate-500);
  padding: 6px;
}
.deleteBtn:hover {
  color: #ff5630;
  background: rgba(255, 86, 48, 0.1);
}

.successText {
  color: var(--primary);
  font-weight: 700;
  font-size: 12.5px;
}
</style>
