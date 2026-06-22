<script setup>
import { onMounted } from "vue";
import {
  Car,
  CreditCard,
  Fuel,
  LogIn,
  LogOut,
  User,
  UserPlus,
  X,
} from "@lucide/vue";

import DoubleSidebar from "./components/DoubleSidebar.vue";
import RecommendationMap from "./components/RecommendationMap.vue";
import FloatingDetailCard from "./components/FloatingDetailCard.vue";
import AuthModal from "./components/AuthModal.vue";
import CardsModalShell from "./components/cards/CardsModalShell.vue";
import VehicleModalShell from "./components/vehicles/VehicleModalShell.vue";
import VehicleView from "./views/VehicleView.vue";
import CardsView from "./views/CardsView.vue";
import { useAuthSession } from "./composables/useAuthSession";
import { useModalState } from "./composables/useModalState";
import { useSmartFuelDashboard } from "./composables/useSmartFuelDashboard";

const {
  activeModal,
  authModalMode,
  openModal,
  closeModal,
  hideModal,
} = useModalState();

let dashboard;
const {
  auth,
  isAuthenticated,
  refreshMe,
  handleAuthenticated,
  handleLogout,
} = useAuthSession({
  afterLogin: async () => Promise.all([dashboard.loadVehicles(), dashboard.loadCards()]),
  clearUserResources: () => dashboard.clearUserResources(),
  resetAfterLogout: () => dashboard.resetAfterLogout(),
  hideModal,
});

dashboard = useSmartFuelDashboard({ isAuthenticated });

const {
  vehicles,
  cards,
  selectedVehicleId,
  location,
  fuel,
  tempCard,
  priority,
  selectedStationId,
  showDetailCard,
  refreshLoading,
  searchRadiusKm,
  recommendation,
  rawCandidates,
  candidates,
  activeRecommendation,
  loadCards,
  handleCloseDetailCard,
  requestRecommendation,
  handleVehicleChanged,
  handleMapLocationSelect,
  handleMapClick,
} = dashboard;

onMounted(refreshMe);
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
