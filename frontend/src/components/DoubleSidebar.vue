<script setup>
import { computed, ref, watch } from "vue";
import {
  ChevronDown,
  ChevronUp,
  CreditCard,
  ListChecks,
  LogIn,
  LogOut,
  MapPin,
  MessageSquare,
  Search,
  Sliders
} from "@lucide/vue";

import LocationControl from "./LocationControl.vue";
import FuelTargetControl from "./FuelTargetControl.vue";
import CardArtwork from "./cards/CardArtwork.vue";
import { NO_DISCOUNT_CARD_ID } from "../composables/useSavedCards.js";
import { discountLabel } from "./cards/cardPresentation.js";
import {
  getVehiclePresentation,
  getVehicleSelectorLabel
} from "./vehicles/vehiclePresentation";

const props = defineProps({
  isAuthenticated: {
    type: Boolean,
    default: false
  },
  user: {
    type: Object,
    default: null
  },
  location: {
    type: Object,
    required: true
  },
  fuel: {
    type: Object,
    required: true
  },
  card: {
    type: Object,
    required: true
  },
  savedVehicles: {
    type: Array,
    default: () => []
  },
  savedCards: {
    type: Array,
    default: () => []
  },
  selectedVehicleId: {
    type: [Number, String],
    default: "manual"
  },
  selectedCardId: {
    type: [Number, String],
    default: NO_DISCOUNT_CARD_ID
  },
  candidates: {
    type: Array,
    default: () => []
  },
  selectedStationId: {
    type: [Number, String],
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  priority: {
    type: String,
    default: "optimal" // 'price', 'distance', 'optimal'
  },
  searchRadiusKm: {
    type: Number,
    default: 5
  }
});

const emit = defineEmits([
  "update:location",
  "update:fuel",
  "update:card",
  "update:selectedCardId",
  "update:selectedVehicleId",
  "update:priority",
  "update:searchRadiusKm",
  "select-station",
  "request-recommendation",
  "go-vehicle-settings",
  "go-card-settings",
  "open-community",
  "logout",
  "login"
]);

// 로컬 동기화용 computed/ref
const activeTab = ref("location"); // "location", "vehicle_card", "settings", "community"
const sidebarOpen = ref(true);
const candidatesExpanded = ref(true);

function toggleCandidates() {
  candidatesExpanded.value = !candidatesExpanded.value;
}

const localLocation = computed({
  get: () => props.location,
  set: (val) => emit("update:location", val)
});

const localFuel = computed({
  get: () => props.fuel,
  set: (val) => emit("update:fuel", val)
});

const localCard = computed({
  get: () => props.card,
  set: (val) => emit("update:card", val)
});

const localSelectedCardId = computed({
  get: () => props.selectedCardId,
  set: (val) => emit("update:selectedCardId", val)
});

const localSelectedVehicleId = computed({
  get: () => props.selectedVehicleId,
  set: (val) => emit("update:selectedVehicleId", val)
});

const localPriority = computed({
  get: () => props.priority,
  set: (val) => emit("update:priority", val)
});

const localRadiusKm = computed({
  get: () => props.searchRadiusKm,
  set: (val) => emit("update:searchRadiusKm", Number(val))
});

const selectedSavedVehicle = computed(() => {
  if (localSelectedVehicleId.value === "manual") return null;
  return props.savedVehicles.find((vehicle) => vehicle.id === localSelectedVehicleId.value) || null;
});

const selectedSavedCard = computed(() => {
  return props.savedCards.find((card) => String(card.card_id) === String(localSelectedCardId.value)) || null;
});

function cardImageSource(card) {
  return card?.card_image_url || card?.card_image_file || "";
}

// 탭 토글 로직
function handleTabClick(tab) {
  if (activeTab.value === tab) {
    sidebarOpen.value = !sidebarOpen.value;
  } else {
    activeTab.value = tab;
    sidebarOpen.value = true;
  }
}

function handleSelectCandidate(stationId) {
  emit("select-station", stationId);
}

const hasResolvedLocation = computed(() => {
  return (
    props.location?.latitude !== null &&
    props.location?.latitude !== undefined &&
    props.location?.latitude !== "" &&
    props.location?.longitude !== null &&
    props.location?.longitude !== undefined &&
    props.location?.longitude !== ""
  );
});

function isPastData(station) {
  if (station.price_source === "database") return true;
  if (!station.price_collected_at) return false;
  const collectedTime = new Date(station.price_collected_at).getTime();
  const now = new Date().getTime();
  return (now - collectedTime) > 24 * 60 * 60 * 1000;
}
</script>


<template>
  <div class="sidebarShell">
    <!-- 1단계: 세로형 슬림 아이콘 탭 바 -->
    <nav class="iconSidebar" aria-label="사이드바 메뉴">
      <div class="tabList">
        <!-- 로고 대신 아이콘으로 연결 -->
        <button type="button" class="tabItem" :class="{ active: activeTab === 'location' && sidebarOpen }" @click="handleTabClick('location')" aria-label="위치 설정" title="위치 설정">
          <Search :size="20" aria-hidden="true" />
          <span>위치</span>
        </button>

        <button type="button" class="tabItem" :class="{ active: activeTab === 'vehicle_card' && sidebarOpen }" @click="handleTabClick('vehicle_card')" aria-label="차량 · 카드" title="차량 · 카드">
          <ListChecks :size="20" aria-hidden="true" />
          <span>차량 · 카드</span>
        </button>

        <button type="button" class="tabItem" :class="{ active: activeTab === 'settings' && sidebarOpen }" @click="handleTabClick('settings')" aria-label="추천 기준" title="추천 기준">
          <Sliders :size="20" aria-hidden="true" />
          <span>추천 기준</span>
        </button>

        <button type="button" class="tabItem" :class="{ active: activeTab === 'community' && sidebarOpen }" @click="handleTabClick('community')" aria-label="커뮤니티" title="커뮤니티">
          <MessageSquare :size="20" aria-hidden="true" />
          <span>커뮤니티</span>
        </button>
      </div>

      <div class="bottomActions">
        <button v-if="isAuthenticated" class="actionItem logout" type="button" @click="emit('logout')" title="로그아웃" aria-label="로그아웃">
          <LogOut :size="18" aria-hidden="true" />
        </button>
        <button v-else class="actionItem" type="button" @click="emit('login')" title="로그인" aria-label="로그인">
          <LogIn :size="18" aria-hidden="true" />
        </button>
      </div>
    </nav>

    <!-- 2단계: 세부 설정 및 결과 패널 -->
    <div class="panelSidebar" :class="{ closed: !sidebarOpen }">
      <!-- 2.1 위치 설정 탭 -->
      <template v-if="activeTab === 'location'">
        <header class="panelSidebarHeader">
          <h2>출발 위치 탐색</h2>
        </header>
        <div class="panelSidebarContent">
          <!-- 위치 검색 연동 -->
          <LocationControl v-model="localLocation" />

          <!-- 주유 금액/유종 선택 간이 제공 -->
          <FuelTargetControl v-model="localFuel" />

          <!-- 검색 반경 제어 셀렉트 박스 -->
          <div class="sidebarSection" style="margin-top: 12px; margin-bottom: 12px; padding: 0; background: transparent; border: none;">
            <label style="display: block;">
              <span style="font-size: 13px; font-weight: 700; color: var(--slate-600); margin-bottom: 6px; display: block;">검색 반경</span>
              <select v-model="localRadiusKm" style="width: 100%; border: 1px solid var(--slate-200); border-radius: var(--radius-sm); padding: 10px 12px; font-size: 13.5px; font-weight: 700; color: var(--slate-700); background-color: #fff; outline: none; transition: border-color 0.2s;">
                <option :value="1">1 km</option>
                <option :value="3">3 km</option>
                <option :value="5">5 km (추천, 실시간 가격)</option>
                <option :value="10">10 km (최근 수집 가격)</option>
                <option :value="15">15 km (최근 수집 가격)</option>
              </select>
            </label>
          </div>

          <!-- 추천 기준 빠른 변경 -->
          <p class="priorityPocketLabel">빠른 설정 변경</p>
          <div class="priorityPocketTabs" role="radiogroup" aria-label="추천 기준 빠른 변경">
            <label class="priorityPocketTab" :class="{ active: localPriority === 'optimal' }">
              <input v-model="localPriority" type="radio" value="optimal" />
              <span>최적</span>
            </label>
            <label class="priorityPocketTab" :class="{ active: localPriority === 'price' }">
              <input v-model="localPriority" type="radio" value="price" />
              <span>가격</span>
            </label>
            <label class="priorityPocketTab" :class="{ active: localPriority === 'distance' }">
              <input v-model="localPriority" type="radio" value="distance" />
              <span>거리</span>
            </label>
          </div>

          <!-- 검색 실행 버튼 -->
          <button
            class="primaryButton fullWidth"
            type="button"
            :disabled="loading || !hasResolvedLocation"
            @click="emit('request-recommendation')"
          >
            <Search :size="16" />
            <span>{{ loading ? "최적가 검색 중..." : hasResolvedLocation ? "맞춤 추천 검색" : "출발지 지정 필요" }}</span>
          </button>
        </div>
      </template>

      <!-- 2.2 차량 & 카드 관리 탭 -->
      <template v-if="activeTab === 'vehicle_card'">
        <header class="panelSidebarHeader">
          <h2>차량 & 할인 혜택</h2>
        </header>
        <div class="panelSidebarContent">
          <!-- 로그인 사용자의 차량 선택 영역 -->
          <div v-if="isAuthenticated" class="sidebarSection">
            <div class="sidebarSectionHeader">
              <h3>등록 차량 목록</h3>
              <button class="inlineFormLink" type="button" @click="emit('go-vehicle-settings')">내 차량 관리 &gt;</button>
            </div>

            <label style="margin-top: 6px;">
              <span>시뮬레이션 주유 차량</span>
              <select v-model="localSelectedVehicleId" :disabled="!savedVehicles.length">
                <option v-if="!savedVehicles.length" value="" disabled>등록 차량이 없습니다</option>
                <option
                  v-for="v in savedVehicles"
                  :key="v.id"
                  :value="v.id"
                >
                  {{ getVehicleSelectorLabel(v) }}
                </option>
                <option value="manual">직접 연비 입력 (수동)</option>
              </select>
            </label>

            <div v-if="selectedSavedVehicle" class="selectedVehiclePreview">
              <img
                :src="getVehiclePresentation(selectedSavedVehicle.vehicle_type).imageUrl"
                :class="getVehiclePresentation(selectedSavedVehicle.vehicle_type).imageClass"
                alt=""
              />
              <div>
                <strong>{{ selectedSavedVehicle.name }}</strong>
                <span>
                  {{ getVehiclePresentation(selectedSavedVehicle.vehicle_type).label }}
                  · {{ Number(selectedSavedVehicle.fuel_efficiency_kmpl).toFixed(1) }} km/L
                </span>
              </div>
            </div>

            <!-- 수동 선택을 대비한 연비 필드 노출 -->
            <div v-if="localSelectedVehicleId === 'manual'" style="margin-top: 12px;">
              <FuelTargetControl v-model="localFuel" :is-read-only="false" />
            </div>
            <p v-else class="hintText" style="margin-top: 8px;">
              선택한 대표 차량의 연료 타입과 연비 조건이 추천 계산에 자동 반영됩니다.
            </p>
          </div>

          <!-- Anonymous vehicle/card login prompt -->
          <div v-else class="sidebarSection loginRequiredSection">
            <div class="loginRequiredIcon">
              <LogIn :size="22" aria-hidden="true" />
            </div>
            <div class="loginRequiredCopy">
              <h3>로그인하여 확인해 보세요</h3>
              <p>
                차량과 할인 카드를 등록하면 저장된 연비와 카드 혜택을 추천 계산에 자동으로 적용할 수 있습니다.
              </p>
            </div>
            <button class="primaryButton fullWidth" type="button" @click="emit('login')">
              <LogIn :size="16" aria-hidden="true" />
              <span>로그인하기</span>
            </button>
          </div>

          <!-- 할인 카드 설정 영역 -->
          <div v-if="isAuthenticated" class="sidebarSection">
            <div class="sidebarSectionHeader">
              <h3>소유한 할인 카드</h3>
              <button class="inlineFormLink" type="button" @click="emit('go-card-settings')">할인 카드 관리 &gt;</button>
            </div>
            <p class="hintText" style="margin: 0 0 10px;">
              이번 가격 산정에 적용할 할인 카드를 선택하세요.
            </p>
            <div v-if="savedCards.length" class="selectedCardPicker">
              <label style="margin-top: 6px;">
                <span>시뮬레이션 할인 카드</span>
                <select v-model="localSelectedCardId">
                  <option :value="NO_DISCOUNT_CARD_ID">카드 혜택 사용 안 함</option>
                  <option
                    v-for="c in savedCards"
                    :key="c.card_id"
                    :value="c.card_id"
                  >
                    {{ c.issuer_name }} · {{ discountLabel(c) }}
                  </option>
                </select>
              </label>

              <div v-if="selectedSavedCard" class="selectedCardPhotoPreview">
                <CardArtwork
                  :src="cardImageSource(selectedSavedCard)"
                  :alt="selectedSavedCard.card_name"
                />
                <div class="selectedCardPhotoCopy">
                  <strong>{{ selectedSavedCard.issuer_name }}</strong>
                  <span>{{ discountLabel(selectedSavedCard) }}</span>
                </div>
              </div>
              <div v-else class="selectedCardPhotoPreview muted">
                <div class="selectedCardNoPhoto">
                  <CreditCard :size="24" aria-hidden="true" />
                </div>
                <div class="selectedCardPhotoCopy">
                  <strong>카드 혜택 미사용</strong>
                  <span>주유 가격과 이동 비용만으로 추천합니다.</span>
                </div>
              </div>
            </div>
            <p v-else class="hintText" style="color: var(--accent); font-weight: 700;">
              등록된 카드가 없습니다. '할인 카드 관리'에서 카드를 등록해 보세요!
            </p>
          </div>

        </div>
      </template>

      <!-- 2.3 추천 우선순위 및 필터 설정 탭 -->
      <template v-if="activeTab === 'settings'">
        <header class="panelSidebarHeader">
          <h2>추천 우선순위 및 설정</h2>
        </header>
        <div class="panelSidebarContent">
          <div class="sidebarSection">
            <div class="sidebarSectionHeader">
              <h3>주유소 추천 우선순위</h3>
            </div>
            <div class="prioritySelector">
              <label class="priorityOption" :class="{ active: localPriority === 'optimal' }">
                <input v-model="localPriority" type="radio" value="optimal" />
                <div class="priorityOptionText">
                  <strong>최적 밸런스 (기본 추천)</strong>
                  <span>연비 고려 이동 비용과 할인 혜택의 완벽한 조화</span>
                </div>
              </label>

              <label class="priorityOption" :class="{ active: localPriority === 'price' }">
                <input v-model="localPriority" type="radio" value="price" />
                <div class="priorityOptionText">
                  <strong>가장 저렴한 곳 (할인가 기준)</strong>
                  <span>이동 거리에 관계없이 최저가 순위 적용</span>
                </div>
              </label>

              <label class="priorityOption" :class="{ active: localPriority === 'distance' }">
                <input v-model="localPriority" type="radio" value="distance" />
                <div class="priorityOptionText">
                  <strong>가장 가까운 곳 (인접 거리)</strong>
                  <span>가장 적게 이동하고 빠르게 방문 가능한 순서</span>
                </div>
              </label>
            </div>
          </div>
        </div>
      </template>

      <!-- 2.4 커뮤니티 탭 -->
      <template v-if="activeTab === 'community'">
        <header class="panelSidebarHeader">
          <h2>커뮤니티</h2>
        </header>
        <div class="panelSidebarContent">
          <div class="sidebarSection communityShortcutSection">
            <div class="sidebarSectionHeader">
              <h3>사용자 커뮤니티</h3>
            </div>
            <p class="hintText" style="margin: 0 0 12px;">
              주유 정보와 차량 관리 팁을 공유하는 커뮤니티로 이동합니다.
            </p>
            <button class="primaryButton fullWidth" type="button" @click="emit('open-community')">
              <MessageSquare :size="16" aria-hidden="true" />
              <span>커뮤니티 열기</span>
            </button>
          </div>
        </div>
      </template>

      <!-- 2.4 공통: 주유소 후보 검색 결과 테이블 (사이드바 하단에 상시 또는 결과 발생 시 노출) -->
      <div v-if="candidates.length" class="sidebarCandidatesSection">
        <button
          class="candidatesAccordionHeader"
          type="button"
          @click="toggleCandidates"
          :aria-expanded="candidatesExpanded"
        >
          <span>📍 근처 추천 주유소 목록 ({{ candidates.length }}개)</span>
          <ChevronDown v-if="candidatesExpanded" :size="16" />
          <ChevronUp v-else :size="16" />
        </button>
        <transition name="accordionSlide">
          <div v-show="candidatesExpanded" class="sidebarCandidateList">
            <div
              v-for="candidate in candidates"
              :key="candidate.station.station_id"
              class="sidebarCandidateRow"
              :class="{ active: selectedStationId === candidate.station.station_id }"
              @click="handleSelectCandidate(candidate.station.station_id)"
            >
              <div class="sidebarCandidateTop">
                <strong>{{ candidate.station.name }}</strong>
                <span class="sidebarCandidateBrand">{{ candidate.station.brand }}</span>
                <span v-if="isPastData(candidate.station)" class="pastDataBadge" style="background-color: var(--accent); color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700; margin-left: 6px; vertical-align: middle;">⚠️ DB 가격</span>
              </div>
              <div class="sidebarCandidateInfo">
                <span>
                  {{ candidate.station.distance_km }} km
                  <template v-if="candidate.station.duration_min">
                    <span style="font-size: 11.5px; color: var(--primary); font-weight: 700; margin-left: 4px;">🚗 {{ Math.round(candidate.station.duration_min) }}분</span>
                  </template>
                </span>
                <span class="price">
                  L당 {{ candidate.station.fuel_price_per_liter.toLocaleString() }}원
                </span>
              </div>
            </div>

          </div>
        </transition>
      </div>
    </div>
  </div>
</template>
