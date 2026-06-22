<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { 
  Car, 
  CreditCard, 
  Fuel, 
  LogIn, 
  LogOut, 
  MapPin,
  User, 
  UserPlus,
  X,
} from "@lucide/vue";

// API Import
import { getCurrentUser, logoutAccount } from "./api/accounts";
import { getMyCards } from "./api/cards";
import { getMyVehicles } from "./api/vehicles";
import { refreshNearbyStations, reverseGeocodeLocation } from "./api/stations";
import { resetCardsWorkspace } from "./stores/cardsWorkspaceStore";
import { recommendationStore } from "./stores/recommendationStore";

// Components Import
import DoubleSidebar from "./components/DoubleSidebar.vue";
import RecommendationMap from "./components/RecommendationMap.vue";
import FloatingDetailCard from "./components/FloatingDetailCard.vue";
import AuthModal from "./components/AuthModal.vue";
import CardsModalShell from "./components/cards/CardsModalShell.vue";
import VehicleModalShell from "./components/vehicles/VehicleModalShell.vue";
import { getVehicleFuelPriceUnit } from "./components/vehicles/vehiclePresentation";

// Views Import for Modal overlay inclusion
import VehicleView from "./views/VehicleView.vue";
import CardsView from "./views/CardsView.vue";

// Reactive State
const auth = reactive({
  loading: true,
  user: null,
  error: null
});

const vehicles = ref([]);
const cards = ref([]);
const selectedVehicleId = ref("manual");

const HOME_LOCATION_STORAGE_KEY = "smartfuel_home_location";

// 추천 및 검색 제어용 Reactive State (기존 RecommendView에서 이관)
const location = reactive({
  latitude: null,
  longitude: null,
  name: "",
  address: "",
  road_address: "",
  jibun_address: "",
  source: "unset",
  accuracy_m: null
});

const fuel = reactive({
  fuel_type: "gasoline",
  target_amount: 50000, // 기본 주유 금액 50,000원
  fuel_efficiency_kmpl: 12.5, // 프로토타입 디폴트 12.5
  travel_mode: "round_trip"
});

// 비로그인 시 임시 카드 시뮬레이터용 데이터
const tempCard = reactive({
  enabled: false,
  card_id: "manual-preview-card",
  card_name: "임시 할인 카드",
  issuer_name: "국민카드",
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

const priority = ref("optimal"); // 'optimal' | 'price' | 'distance'
const selectedStationId = ref(null);
const showDetailCard = ref(false);
const stationRefreshMessage = ref("");
const refreshLoading = ref(false);

// 모달 제어 상태 ('auth' | 'vehicle' | 'cards' | null)
const activeModal = ref(null);
const modalReturnFocus = ref(null);
const authModalMode = ref("login");

// Computed Properties
const vehicle = computed(() => {
  return vehicles.value.find(v => v.is_default) || vehicles.value[0] || null;
});

const isAuthenticated = computed(() => Boolean(auth.user));

const response = computed(() => recommendationStore.response);
const recommendation = computed(() => response.value?.recommendation || null);
const rawCandidates = computed(() => response.value?.candidates || []);

// 추천 우선순위 정렬은 백엔드가 결정하므로 응답 순서를 그대로 표시한다.
const candidates = computed(() => {
  return rawCandidates.value;
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

const isVehicleProfileApplied = computed(() => {
  return selectedVehicleId.value !== "manual" && selectedVehicleId.value !== null;
});

const searchRadiusKm = ref(5);

let hasLoadedPersistedLocation = false;
let mapLocationRequestId = 0;

function isValidCoordinate(latitude, longitude) {
  const lat = Number(latitude);
  const lon = Number(longitude);
  return Number.isFinite(lat) && Number.isFinite(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
}

function normalizeLocationPayload(payload) {
  if (!payload || !isValidCoordinate(payload.latitude, payload.longitude)) {
    return null;
  }

  return {
    latitude: Number(payload.latitude),
    longitude: Number(payload.longitude),
    name: payload.name || payload.address || "저장된 출발지",
    address: payload.address || payload.road_address || payload.jibun_address || "",
    road_address: payload.road_address || "",
    jibun_address: payload.jibun_address || "",
    source: payload.source || "stored",
    accuracy_m: payload.accuracy_m ?? null,
    saved_at: payload.saved_at || new Date().toISOString()
  };
}

function applyLocationPayload(payload) {
  const normalized = normalizeLocationPayload(payload);
  if (!normalized) return false;
  Object.assign(location, normalized);
  return true;
}

function applyStartLocationPayload(payload) {
  const applied = applyLocationPayload(payload);
  if (!applied) return false;

  selectedStationId.value = null;
  showDetailCard.value = false;
  recommendationStore.response = null;
  recommendationStore.error = null;
  return true;
}

function loadPersistedLocation() {
  try {
    const raw = window.localStorage.getItem(HOME_LOCATION_STORAGE_KEY);
    if (!raw) return false;
    return applyLocationPayload(JSON.parse(raw));
  } catch (error) {
    window.localStorage.removeItem(HOME_LOCATION_STORAGE_KEY);
    return false;
  }
}

function persistLocation() {
  const normalized = normalizeLocationPayload(location);
  if (!normalized) return;
  window.localStorage.setItem(
    HOME_LOCATION_STORAGE_KEY,
    JSON.stringify({
      ...normalized,
      saved_at: new Date().toISOString()
    })
  );
}

function getBrowserPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("GEOLOCATION_UNAVAILABLE"));
      return;
    }

    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 8000,
      maximumAge: 30000
    });
  });
}

async function canUseStoredGeolocationPermission() {
  if (!navigator.permissions?.query) {
    return false;
  }

  try {
    const permission = await navigator.permissions.query({ name: "geolocation" });
    return permission.state === "granted";
  } catch (error) {
    return false;
  }
}

async function initializeBrowserLocationIfGranted() {
  if (!(await canUseStoredGeolocationPermission())) {
    return false;
  }

  try {
    const position = await getBrowserPosition();
    const latitude = Number(position.coords.latitude.toFixed(6));
    const longitude = Number(position.coords.longitude.toFixed(6));
    const payload = {
      latitude,
      longitude,
      name: "현재 위치",
      address: "",
      source: "browser_geolocation",
      accuracy_m: position.coords.accuracy
    };

    try {
      const response = await reverseGeocodeLocation(latitude, longitude);
      if (response.result) {
        Object.assign(payload, response.result, {
          source: "browser_geolocation",
          accuracy_m: position.coords.accuracy
        });
      }
    } catch (error) {
      // 좌표만으로도 출발지 설정은 가능하므로 역지오코딩 실패는 치명적이지 않다.
    }

    return applyLocationPayload(payload);
  } catch (error) {
    return false;
  }
}

// Methods
watch(
  () => [location.latitude, location.longitude, location.name, location.address, location.source, location.accuracy_m],
  () => {
    if (!hasLoadedPersistedLocation || !isValidCoordinate(location.latitude, location.longitude)) {
      return;
    }
    persistLocation();
  }
);

watch(recommendation, (nextRecommendation) => {
  selectedStationId.value = nextRecommendation?.station?.station_id || null;
  if (nextRecommendation) {
    showDetailCard.value = true;
  } else {
    showDetailCard.value = false;
  }
});

watch(selectedStationId, (id) => {
  if (id) {
    showDetailCard.value = true;
  }
});

function handleCloseDetailCard() {
  showDetailCard.value = false;
  selectedStationId.value = null;
}

watch(
  () => vehicles.value,
  (list) => {
    if (list && list.length > 0) {
      const defaultVehicle = list.find(v => v.is_default) || list[0];
      selectedVehicleId.value = defaultVehicle.id;
      fuel.fuel_type = defaultVehicle.fuel_type;
      fuel.fuel_efficiency_kmpl = Number(defaultVehicle.fuel_efficiency_kmpl);
    } else {
      selectedVehicleId.value = "manual";
    }
  },
  { immediate: true }
);

watch(selectedVehicleId, (id) => {
  if (id === "manual" || !vehicles.value) return;
  const found = vehicles.value.find(v => v.id === id);
  if (found) {
    fuel.fuel_type = found.fuel_type;
    fuel.fuel_efficiency_kmpl = Number(found.fuel_efficiency_kmpl);
  }
});

async function refreshMe() {
  auth.loading = true;
  auth.error = null;
  try {
    const payload = await getCurrentUser();
    auth.user = payload.authenticated ? payload.user : null;
    if (auth.user) {
      await Promise.all([loadVehicles(), loadCards()]);
    } else {
      vehicles.value = [];
      cards.value = [];
    }
  } catch (error) {
    auth.error = error.payload || { message: error.message };
  } finally {
    auth.loading = false;
  }
}

async function loadVehicles() {
  try {
    const payload = await getMyVehicles();
    vehicles.value = payload.vehicles || [];
  } catch (error) {
    if (error.status !== 404) throw error;
    vehicles.value = [];
  }
}

async function loadCards() {
  const payload = await getMyCards();
  cards.value = payload.cards || [];
}

async function handleLogout() {
  await logoutAccount();
  activeModal.value = null;
  resetCardsWorkspace();
  auth.user = null;
  vehicles.value = [];
  cards.value = [];
  selectedVehicleId.value = "manual";
  recommendationStore.response = null;
  selectedStationId.value = null;
}

async function handleAuthenticated(user) {
  auth.user = user;
  activeModal.value = null;
  await Promise.all([loadVehicles(), loadCards()]);
}

function openModal(modalType, extra = null) {
  if (modalType === "auth") {
    authModalMode.value = extra || "login";
  }
  modalReturnFocus.value = document.activeElement;
  activeModal.value = modalType;
}

function closeModal() {
  activeModal.value = null;
  requestAnimationFrame(() => modalReturnFocus.value?.focus?.());
}

async function handleVehicleChanged() {
  await loadVehicles();
  if (recommendationStore.response && location.latitude && location.longitude) {
    await requestRecommendation();
    return;
  }
  recommendationStore.response = null;
  selectedStationId.value = null;
  showDetailCard.value = false;
}

function optionalNumber(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  return Number(value);
}

function selectedCards() {
  // 로그인 유저의 경우 저장된 모든 카드를 API에 실어서 보냄
  if (isAuthenticated.value) {
    return cards.value.map(c => ({
      card_id: c.card_id,
      card_name: c.card_name,
      issuer_name: c.issuer_name,
      discount_type: c.discount_type,
      discount_value: Number(c.discount_value || 0),
      brand_scope: c.brand_scope || "all",
      min_payment_amount: optionalNumber(c.min_payment_amount),
      max_discount_amount: optionalNumber(c.max_discount_amount),
      monthly_remaining_discount: optionalNumber(c.monthly_remaining_discount)
    }));
  }

  // 비로그인 유저의 경우 임시 카드 시뮬레이터 반영
  if (!tempCard.enabled) {
    return [];
  }

  return [
    {
      card_id: tempCard.card_id,
      card_name: tempCard.card_name,
      issuer_name: tempCard.issuer_name,
      discount_type: tempCard.discount_type,
      discount_value: Number(tempCard.discount_value || 0),
      brand_scope: tempCard.brand_scope || "all",
      min_payment_amount: optionalNumber(tempCard.min_payment_amount),
      max_discount_amount: optionalNumber(tempCard.max_discount_amount),
      monthly_remaining_discount: optionalNumber(tempCard.monthly_remaining_discount)
    }
  ];
}

// 실시간 최적화 추천 요청 실행 함수
async function requestRecommendation() {
  if (!location.latitude || !location.longitude) {
    recommendationStore.error = {
      code: "MISSING_LOCATION",
      message: "출발 위치를 먼저 확정해 주세요."
    };
    return;
  }

  const priceUnit = getVehicleFuelPriceUnit(fuel.fuel_type);
  const calculatedLiters = Number((fuel.target_amount / priceUnit).toFixed(2));

  const request = {
    location: {
      latitude: location.latitude,
      longitude: location.longitude
    },
    fuel_type: fuel.fuel_type,
    radius_km: searchRadiusKm.value,
    recommendation_priority: priority.value,
    target_liters: calculatedLiters,
    travel_mode: fuel.travel_mode,
    cards: selectedCards(),
    include_candidates: true,
    vehicle: {
      fuel_efficiency_kmpl: fuel.fuel_efficiency_kmpl
    }
  };

  refreshLoading.value = true;
  stationRefreshMessage.value = "주변 주유소 데이터를 확인하는 중입니다.";

  try {
    const refresh = await refreshNearbyStations({
      location: request.location,
      fuel_type: request.fuel_type,
      radius_km: Math.min(searchRadiusKm.value, 5)
    });

    const rows = refresh?.meta?.rows || 0;
    stationRefreshMessage.value = 
      refresh.status === "ok"
        ? `주변 주유소 ${rows.toLocaleString("ko-KR")}건을 반영했습니다.`
        : "저장된 최신 주유소 데이터로 계산합니다.";
  } catch (error) {
    stationRefreshMessage.value = "저장된 기존 주유소 정보로 연산을 수행합니다.";
  }

  try {
    await recommendationStore.quote(request);
  } catch (error) {
    // 추천 계산 에러는 UI에서 처리 (프로덕션 콘솔 출력 제거)
  } finally {
    refreshLoading.value = false;
  }
}

function handleMapLocationSelect(payload) {
  applyStartLocationPayload({
    ...payload,
    source: payload.source || "naver_map_search"
  });
}

async function handleMapClick(coords) {
  const latitude = Number(coords.latitude);
  const longitude = Number(coords.longitude);
  if (!isValidCoordinate(latitude, longitude)) return;

  const requestId = ++mapLocationRequestId;
  const payload = {
    latitude,
    longitude,
    name: "지도에서 지정한 위치",
    address: "",
    source: coords.source || "map_click",
    accuracy_m: null
  };

  applyStartLocationPayload(payload);

  try {
    const response = await reverseGeocodeLocation(latitude, longitude);
    if (requestId !== mapLocationRequestId || !response.result) return;
    applyStartLocationPayload({
      ...payload,
      ...response.result,
      source: coords.source || "map_click",
      accuracy_m: null
    });
  } catch (error) {
    // 지도 클릭 좌표만으로도 출발지 설정은 가능하므로 역지오코딩 실패는 치명적이지 않다.
  }
}

onMounted(async () => {
  const restored = loadPersistedLocation();
  hasLoadedPersistedLocation = true;
  if (!restored) {
    await initializeBrowserLocationIfGranted();
  }
  refreshMe();
});
</script>

<template>
  <div class="appShellUnified">
    <div
      class="appBackground"
      :inert="activeModal === 'vehicle' || activeModal === 'cards'"
      :aria-hidden="activeModal === 'vehicle' || activeModal === 'cards' ? 'true' : undefined"
    >
    <!-- 상단 글래스모피즘 헤더 바 -->
    <header class="topBarUnified">
      <div class="logoContainer" @click="selectedStationId = null" title="새로고침">
        <Fuel :size="22" style="color: var(--primary);" />
        <h1>SmartFuel</h1>
      </div>

      <div class="navLinks">
        <button 
          v-if="isAuthenticated" 
          class="linkBtn" 
          :class="{ active: activeModal === 'vehicle' }" 
          type="button" 
          @click="openModal('vehicle')"
        >
          <Car :size="15" />
          <span>내 차량 설정</span>
        </button>

        <button 
          v-if="isAuthenticated" 
          class="linkBtn" 
          :class="{ active: activeModal === 'cards' }" 
          type="button" 
          @click="openModal('cards')"
        >
          <CreditCard :size="15" />
          <span>할인 카드 관리</span>
        </button>
      </div>

      <div class="userSection">
        <div v-if="isAuthenticated" class="userIndicator">
          <User :size="14" style="color: var(--primary);" />
          <strong>{{ auth.user.username }}</strong>님
        </div>
        <button v-if="isAuthenticated" class="linkBtn" type="button" @click="handleLogout">
          <LogOut :size="14" />
          <span>로그아웃</span>
        </button>
        <button v-else class="linkBtn" type="button" @click="openModal('auth', 'login')">
          <LogIn :size="14" />
          <span>로그인</span>
        </button>
        <button v-if="!isAuthenticated" class="linkBtn" type="button" @click="openModal('auth', 'signup')">
          <UserPlus :size="14" />
          <span>회원 가입</span>
        </button>
      </div>
    </header>

    <!-- 올인원 통합 맵 대시보드 뷰 -->
    <main class="unifiedDashboard">
      <!-- 더블 사이드바 장착 -->
      <DoubleSidebar
        v-model:location="location"
        v-model:fuel="fuel"
        v-model:card="tempCard"
        v-model:selectedVehicleId="selectedVehicleId"
        v-model:priority="priority"
        v-model:searchRadiusKm="searchRadiusKm"
        :is-authenticated="isAuthenticated"

        :user="auth.user"
        :saved-vehicles="vehicles"
        :saved-cards="cards"
        :candidates="candidates"
        :selected-station-id="selectedStationId"
        :loading="refreshLoading"
        @select-station="selectedStationId = $event"
        @request-recommendation="requestRecommendation"
        @go-vehicle-settings="openModal('vehicle')"
        @go-card-settings="openModal('cards')"
        @login="openModal('auth', 'login')"
        @logout="handleLogout"
      />

      <!-- 풀스크린 네이버 지도 장착 -->
      <RecommendationMap
        :recommendation="recommendation"
        :candidates="rawCandidates"
        :selected-station-id="selectedStationId"
        :user-location="location"
        @select="selectedStationId = $event"
        @location-select="handleMapLocationSelect"
        @map-click="handleMapClick"
      />

      <!-- 우측 하단 상세 정보 플로팅 카드 -->
      <transition name="fadeSlide">
        <FloatingDetailCard
          v-if="activeRecommendation && showDetailCard"
          :recommendation="activeRecommendation"
          @close="handleCloseDetailCard"
          @detail="openModal('detail', $event)"
        />
      </transition>
    </main>
    </div>

    <!-- ==========================================
         글래스모피즘 오버레이 모달 시스템
         ========================================== -->

    <!-- 1. 인증(로그인 / 회원가입) 모달 -->
    <AuthModal
      v-if="activeModal === 'auth'"
      :initial-mode="authModalMode"
      @close="closeModal"
      @authenticated="handleAuthenticated"
    />

    <!-- 2. 내 차량 설정 관리 모달 -->
    <VehicleModalShell v-if="activeModal === 'vehicle'" @close="closeModal">
      <VehicleView
        :vehicles="vehicles"
        @changed="handleVehicleChanged"
      />
    </VehicleModalShell>

    <!-- 3. 내 할인 카드 관리 모달 -->
    <CardsModalShell v-if="activeModal === 'cards'" @close="closeModal">
      <CardsView :cards="cards" @changed="loadCards" />
    </CardsModalShell>

    <!-- 4. 주유소 최종 상세 분석 분석 팝업 모달 -->
    <div v-if="activeModal === 'detail'" class="glassModalOverlay" @click.self="closeModal">
      <div class="glassModalContainer" style="max-width: 520px; padding: 32px;">
        <header class="glassModalHeader">
          <h2>주유 분석 상세 정보</h2>
          <button class="glassModalCloseBtn" type="button" @click="closeModal" aria-label="닫기">
            <X :size="16" />
          </button>
        </header>
        
        <div v-if="activeRecommendation" style="border: none; padding: 0; box-shadow: none;">
          <div class="resultTop" style="margin-bottom: 16px;">
            <div>
              <p class="eyebrow" style="color: var(--primary);">{{ activeRecommendation.station.brand }}</p>
              <h2 style="font-size: 20px; font-weight: 900; color: var(--slate-900);">{{ activeRecommendation.station.name }}</h2>
              <p style="font-size: 12px; color: var(--slate-500); margin: 6px 0 0;">{{ activeRecommendation.station.address }}</p>
            </div>
          </div>

          <div style="background: var(--slate-50); border-radius: var(--radius-md); padding: 16px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; color: var(--slate-600); margin-bottom: 8px;">
              <span>주유 용량</span>
              <span>{{ activeRecommendation.cost_breakdown.target_liters }} L</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; color: var(--slate-600); margin-bottom: 8px;">
              <span>원가 기준 주유비</span>
              <span>{{ activeRecommendation.cost_breakdown.refuel_cost.toLocaleString() }}원</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; color: var(--secondary); margin-bottom: 8px;">
              <span>카드 제휴 할인</span>
              <span>-{{ activeRecommendation.cost_breakdown.card_discount_amount.toLocaleString() }}원</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; color: #ef4444; margin-bottom: 8px;">
              <span>이동 연비 비용</span>
              <span>+{{ activeRecommendation.cost_breakdown.travel_cost.toLocaleString() }}원</span>
            </div>
            <div style="border-top: 1px dashed var(--slate-200); margin-top: 12px; padding-top: 12px; display: flex; justify-content: space-between; font-size: 15px; font-weight: 900; color: var(--slate-900);">
              <span>최종 체감 실비용</span>
              <span style="color: var(--primary);">{{ activeRecommendation.cost_breakdown.effective_total_cost.toLocaleString() }}원</span>
            </div>
          </div>

          <p class="reason" style="margin: 0; line-height: 1.6; font-size: 13.5px; border-left-color: var(--primary);">
            {{ activeRecommendation.reason }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.spinIcon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
