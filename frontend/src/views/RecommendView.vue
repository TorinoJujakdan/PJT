<script setup>
import { computed, reactive, ref, watch } from "vue";
import { Search } from "@lucide/vue";
import CardPolicyForm from "../components/CardPolicyForm.vue";
import CandidateList from "../components/CandidateList.vue";
import FuelTargetControl from "../components/FuelTargetControl.vue";
import LocationControl from "../components/LocationControl.vue";
import RecommendationContextPanel from "../components/RecommendationContextPanel.vue";
import RecommendationMap from "../components/RecommendationMap.vue";
import RecommendationResult from "../components/RecommendationResult.vue";
import { recommendationStore } from "../stores/recommendationStore";

const props = defineProps({
  isAuthenticated: {
    type: Boolean,
    default: false
  },
  savedVehicle: {
    type: Object,
    default: null
  },
  savedVehicles: {
    type: Array,
    default: () => []
  },
  savedCards: {
    type: Array,
    default: () => []
  }
});
const emit = defineEmits(["go-vehicle", "go-cards"]);

const selectedVehicleId = ref(null);

const location = reactive({
  latitude: 37.501,
  longitude: 127.039
});

const fuel = reactive({
  fuel_type: "gasoline",
  target_amount: 50000, // 기본 주유 금액 셋팅: 50,000원
  fuel_efficiency_kmpl: 10,
  travel_mode: "round_trip"
});

const card = reactive({
  enabled: false,
  card_id: "manual-preview-card",
  card_name: "주유 할인 카드",
  issuer_name: "내 카드사",
  discount_type: "per_liter",
  discount_value: 80,
  brand_scope: "all",
  min_payment_amount: null,
  max_discount_amount: 5000,
  monthly_remaining_discount: 12000,
  source_type: "manual",
  verification_status: "user_confirmed",
  card_image_url: null,
  source_url: null
});

const response = computed(() => recommendationStore.response);
const recommendation = computed(() => response.value?.recommendation || null);
const candidates = computed(() => response.value?.candidates || []);
const selectedStationId = ref(null);
const isVehicleProfileApplied = computed(() => {
  return selectedVehicleId.value !== "manual" && selectedVehicleId.value !== null;
});

const activeRecommendation = computed(() => {
  if (!response.value) return null;
  const mainRec = response.value.recommendation;
  if (!selectedStationId.value || mainRec?.station?.station_id === selectedStationId.value) {
    return mainRec;
  }
  const found = response.value.candidates?.find(
    (c) => c.station?.station_id === selectedStationId.value
  );
  return found || mainRec;
});

watch(recommendation, (nextRecommendation) => {
  selectedStationId.value = nextRecommendation?.station?.station_id || null;
});

function getFuelTypeName(type) {
  const names = {
    gasoline: "휘발유",
    diesel: "경유",
    lpg: "LPG",
    premium_gasoline: "고급 휘발유"
  };
  return names[type] || type;
}

watch(
  () => props.savedVehicles,
  (vehicles) => {
    if (vehicles && vehicles.length > 0) {
      const defaultVehicle = vehicles.find(v => v.is_default) || vehicles[0];
      selectedVehicleId.value = defaultVehicle.id;
      fuel.fuel_type = defaultVehicle.fuel_type;
      fuel.fuel_efficiency_kmpl = Number(defaultVehicle.fuel_efficiency_kmpl);
    } else {
      selectedVehicleId.value = "manual";
    }
  },
  { immediate: true, deep: true }
);

watch(selectedVehicleId, (id) => {
  if (id === "manual" || !props.savedVehicles) return;
  const found = props.savedVehicles.find(v => v.id === id);
  if (found) {
    fuel.fuel_type = found.fuel_type;
    fuel.fuel_efficiency_kmpl = Number(found.fuel_efficiency_kmpl);
  }
});

function optionalNumber(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  return Number(value);
}

function selectedCards() {
  if (!card.enabled) {
    return [];
  }

  return [
    {
      card_id: card.card_id,
      card_name: card.card_name,
      issuer_name: card.issuer_name,
      discount_type: card.discount_type,
      discount_value: Number(card.discount_value || 0),
      brand_scope: card.brand_scope || "all",
      min_payment_amount: optionalNumber(card.min_payment_amount),
      max_discount_amount: optionalNumber(card.max_discount_amount),
      monthly_remaining_discount: optionalNumber(card.monthly_remaining_discount),
      source_type: card.source_type,
      verification_status: card.verification_status,
      card_image_url: card.card_image_url,
      source_url: card.source_url
    }
  ];
}

function getFuelPriceUnit(type) {
  if (type === "diesel") return 1500;
  if (type === "lpg") return 1000;
  if (type === "premium_gasoline") return 1850;
  return 1650; // gasoline
}

function requestRecommendation() {
  const priceUnit = getFuelPriceUnit(fuel.fuel_type);
  const calculatedLiters = Number((fuel.target_amount / priceUnit).toFixed(2));

  const request = {
    location: {
      latitude: location.latitude,
      longitude: location.longitude
    },
    fuel_type: fuel.fuel_type,
    target_liters: calculatedLiters,
    travel_mode: fuel.travel_mode,
    cards: selectedCards(),
    include_candidates: true,
    vehicle: {
      fuel_efficiency_kmpl: fuel.fuel_efficiency_kmpl
    }
  };

  recommendationStore.quote(request);
}
</script>

<template>
  <div class="workspace">
    <aside class="controls">
      <RecommendationContextPanel
        :is-authenticated="isAuthenticated"
        :saved-vehicle="savedVehicle"
        :saved-cards="savedCards"
        :use-saved-vehicle="canUseSavedVehicle"
        @go-vehicle="emit('go-vehicle')"
        @go-cards="emit('go-cards')"
      />

      <LocationControl v-model="location" />

      <section v-if="isAuthenticated" class="panel">
        <div class="panelHeader">
          <div>
            <p class="eyebrow">Simulate Account Info</p>
            <h2>시뮬레이션 차량 선택</h2>
          </div>
        </div>
        
        <div class="fieldGrid">
          <label>
            <span>주유할 차량</span>
            <select v-model="selectedVehicleId" :disabled="!savedVehicles.length">
              <option v-if="!savedVehicles.length" value="" disabled>등록된 차량 없음</option>
              <option
                v-for="v in savedVehicles"
                :key="v.id"
                :value="v.id"
              >
                {{ getFuelTypeName(v.fuel_type) }} ({{ Number(v.fuel_efficiency_kmpl).toFixed(1) }} km/L){{ v.is_default ? ' [대표]' : '' }}
              </option>
              <option value="manual">직접 입력 (수동 설정)</option>
            </select>
          </label>
        </div>
        
        <p class="hintText" style="margin-top: 10px;">
          선택한 차량의 유종과 연비가 계산 모델에 실시간 적용됩니다.<br />
          등록된 내 할인 카드 {{ savedCards.length }}개가 추천 계산에 자동 포함됩니다.
        </p>
      </section>

      <FuelTargetControl v-model="fuel" :is-read-only="isVehicleProfileApplied" />

      <CardPolicyForm v-model="card" :cards="savedCards" />

      <button class="primaryButton fullWidth" type="button" :disabled="recommendationStore.loading" @click="requestRecommendation">
        <Search :size="18" />
        <span>{{ recommendationStore.loading ? "계산 중" : "추천 받기" }}</span>
      </button>
    </aside>

    <section class="results">
      <div v-if="recommendationStore.error" class="errorPanel">
        <strong>{{ recommendationStore.error.code }}</strong>
        <span>{{ recommendationStore.error.message }}</span>
      </div>

      <RecommendationResult v-if="activeRecommendation" :recommendation="activeRecommendation" />

      <RecommendationMap
        v-if="recommendation"
        :recommendation="recommendation"
        :candidates="candidates"
        :selected-station-id="selectedStationId"
        @select="selectedStationId = $event"
      />

      <section v-else class="emptyState">
        <p class="eyebrow">Ready</p>
        <h2>조건을 입력하고 추천을 요청하세요</h2>
      </section>

      <CandidateList
        v-if="candidates.length"
        :candidates="candidates"
        :selected-station-id="selectedStationId"
        @select="selectedStationId = $event"
      />
    </section>
  </div>
</template>
