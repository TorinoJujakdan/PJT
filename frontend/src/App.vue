<script setup>
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Car, CreditCard, Fuel, LogIn, LogOut, User, UserPlus } from "@lucide/vue";
import { getCurrentUser, logoutAccount } from "./api/accounts";
import { getMyCards } from "./api/cards";
import { getMyVehicles } from "./api/vehicles";
import CardsView from "./views/CardsView.vue";
import LoginView from "./views/LoginView.vue";
import ProfileView from "./views/ProfileView.vue";
import RecommendView from "./views/RecommendView.vue";
import SignupView from "./views/SignupView.vue";
import VehicleView from "./views/VehicleView.vue";

const activeView = ref("recommend");
const auth = reactive({
  loading: true,
  user: null,
  error: null
});
const vehicles = ref([]);
const cards = ref([]);

const vehicle = computed(() => {
  return vehicles.value.find(v => v.is_default) || vehicles.value[0] || null;
});

const isAuthenticated = computed(() => Boolean(auth.user));

// Simple Hash Routing Implementation for Browser Back/Forward navigation support
function syncHashWithView() {
  const hash = window.location.hash.replace(/^#\/?/, "");
  const validViews = ["recommend", "profile", "cards", "login", "signup", "vehicle"];
  if (validViews.includes(hash)) {
    activeView.value = hash;
  } else {
    activeView.value = "recommend";
    window.location.hash = "#/recommend";
  }
}

watch(activeView, (newView) => {
  if (window.location.hash.replace(/^#\/?/, "") !== newView) {
    window.location.hash = `#/${newView}`;
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
  auth.user = null;
  vehicles.value = [];
  cards.value = [];
  activeView.value = "recommend";
}

async function handleAuthenticated(user) {
  auth.user = user;
  activeView.value = "recommend";
  Promise.all([loadVehicles(), loadCards()]);
}

async function handleVehicleSaved() {
  await loadVehicles();
  activeView.value = "recommend";
}

function setView(viewName) {
  activeView.value = viewName;
}


onMounted(() => {
  refreshMe();
  syncHashWithView();
  window.addEventListener("hashchange", syncHashWithView);
});

onBeforeUnmount(() => {
  window.removeEventListener("hashchange", syncHashWithView);
});
</script>

<template>
  <div class="appShell">
    <header class="topBar">
      <div @click="setView('recommend')" style="cursor: pointer;" title="메인 화면으로 이동">
        <p class="eyebrow">SmartFuel Platform</p>
        <h1>실제 비용 주유 최적화</h1>
      </div>
      <nav class="navBar" aria-label="주요 메뉴">
        <button class="navButton" :class="{ active: activeView === 'recommend' }" type="button" @click="setView('recommend')">
          <Fuel :size="16" />
          <span>주유 추천</span>
        </button>
        <button
          v-if="isAuthenticated"
          class="navButton"
          :class="{ active: activeView === 'vehicle' }"
          type="button"
          @click="setView('vehicle')"
        >
          <Car :size="16" />
          <span>내 차량 설정</span>
        </button>

        <button
          v-if="isAuthenticated"
          class="navButton"
          :class="{ active: activeView === 'profile' }"
          type="button"
          @click="setView('profile')"
        >
          <User :size="16" />
          <span>마이페이지</span>
        </button>
        <button
          v-if="isAuthenticated"
          class="navButton"
          :class="{ active: activeView === 'cards' }"
          type="button"
          @click="setView('cards')"
        >
          <CreditCard :size="16" />
          <span>내 할인 카드</span>
        </button>
        <button
          v-if="!isAuthenticated"
          class="navButton"
          :class="{ active: activeView === 'login' }"
          type="button"
          @click="setView('login')"
        >
          <LogIn :size="16" />
          <span>로그인</span>
        </button>
        <button
          v-if="!isAuthenticated"
          class="navButton"
          :class="{ active: activeView === 'signup' }"
          type="button"
          @click="setView('signup')"
        >
          <UserPlus :size="16" />
          <span>회원 가입</span>
        </button>
        <button v-if="isAuthenticated" class="navButton" type="button" @click="handleLogout">
          <LogOut :size="16" />
          <span>로그아웃</span>
        </button>
      </nav>
    </header>

    <div class="statusStrip">
      <span v-if="auth.loading">안전하게 사용자 정보를 불러오는 중입니다...</span>
      <span v-else-if="isAuthenticated"><strong>{{ auth.user.username }}</strong>님 환영합니다! 등록된 차량 정보와 할인 카드를 통해 실시간 100% 맞춤 추천이 작동하고 있습니다.</span>
      <span v-else>현재 비로그인 탐색 중입니다. 연비와 주유량을 직접 입력하여 주유 비용을 시뮬레이션할 수 있습니다.</span>
    </div>

    <RecommendView
      v-if="activeView === 'recommend'"
      :is-authenticated="isAuthenticated"
      :saved-vehicle="vehicle"
      :saved-vehicles="vehicles"
      :saved-cards="cards"
      @go-vehicle="setView('vehicle')"
      @go-cards="setView('cards')"
    />
    <LoginView v-else-if="activeView === 'login'" @authenticated="handleAuthenticated" @go-signup="setView('signup')" />
    <SignupView v-else-if="activeView === 'signup'" @authenticated="handleAuthenticated" @go-login="setView('login')" />
    <ProfileView
      v-else-if="activeView === 'profile'"
      :user="auth.user"
      :vehicle="vehicle"
      :cards="cards"
      @go-vehicle="setView('vehicle')"
      @go-cards="setView('cards')"
      @updated="refreshMe"
    />
    <VehicleView v-else-if="activeView === 'vehicle'" :vehicle="vehicle" :vehicles="vehicles" @saved="handleVehicleSaved" @changed="loadVehicles" />
    <CardsView v-else-if="activeView === 'cards'" :cards="cards" @changed="loadCards" />
  </div>
</template>

