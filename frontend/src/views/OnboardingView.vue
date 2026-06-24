<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import {
  ArrowRight,
  Car,
  CreditCard,
  Fuel,
  LogIn,
  MapPin,
  Sparkles,
  UserPlus,
  Users,
} from "@lucide/vue";

import { signupAccount } from "../api/accounts";
import { addVehicle } from "../api/vehicles";
import VehicleTypePicker from "../components/vehicles/VehicleTypePicker.vue";
import {
  VEHICLE_FUEL_LABELS,
  VEHICLE_TYPES,
  buildVehiclePayload,
  getVehiclePresentation,
} from "../components/vehicles/vehiclePresentation";

const emit = defineEmits(["login", "authenticated"]);

const DRAFT_KEY = "smartfuel:onboarding-draft";
const DEFAULT_EFFICIENCY = 10;

const mode = ref("landing");
const loading = ref(false);
const error = ref(null);
const vehicleWarning = ref("");

const setupForm = reactive({
  fuel_type: "gasoline",
  vehicle_type: "sedan",
});

const signupForm = reactive({
  username: "",
  email: "",
  password: "",
});

const featureCards = [
  {
    icon: MapPin,
    eyebrow: "LOCATION",
    title: "지금 위치에서 가까운 주유소를 비교해요",
    description: "검색 반경과 출발 위치를 기준으로 후보 주유소를 빠르게 정리합니다.",
  },
  {
    icon: CreditCard,
    eyebrow: "BENEFIT",
    title: "카드 할인까지 반영한 체감가를 보여줘요",
    description: "주유 가격만 보지 않고 이동비와 할인 혜택을 함께 계산합니다.",
  },
  {
    icon: Sparkles,
    eyebrow: "MATCH",
    title: "최적·가격·거리 기준으로 추천 방식을 바꿔요",
    description: "상황에 맞게 가장 싼 곳, 가까운 곳, 균형 잡힌 곳을 고를 수 있습니다.",
  },
  {
    icon: Users,
    eyebrow: "COMMUNITY",
    title: "주유 팁과 경험을 커뮤니티에서 나눠요",
    description: "다른 운전자의 카드·주유소 활용 팁을 참고할 수 있습니다.",
  },
];

const selectedVehicle = computed(() => getVehiclePresentation(setupForm.vehicle_type));

function readDraft() {
  if (typeof localStorage === "undefined") return;
  try {
    const parsed = JSON.parse(localStorage.getItem(DRAFT_KEY) || "{}");
    if (parsed.fuel_type && VEHICLE_FUEL_LABELS[parsed.fuel_type]) {
      setupForm.fuel_type = parsed.fuel_type;
    }
    if (parsed.vehicle_type && VEHICLE_TYPES.some(({ value }) => value === parsed.vehicle_type)) {
      setupForm.vehicle_type = parsed.vehicle_type;
    }
  } catch {
    localStorage.removeItem(DRAFT_KEY);
  }
}

function writeDraft() {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(
    DRAFT_KEY,
    JSON.stringify({
      fuel_type: setupForm.fuel_type,
      vehicle_type: setupForm.vehicle_type,
    })
  );
}

function clearDraft() {
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem(DRAFT_KEY);
}

function startOnboarding() {
  mode.value = "onboarding";
  writeDraft();
}

function readableError(err, fallback) {
  const details = err?.payload?.details;
  if (details && typeof details === "object") {
    const first = Object.values(details).flat()[0];
    if (first) return String(first);
  }
  return err?.payload?.message || err?.message || fallback;
}

async function createDefaultVehicle() {
  const payload = buildVehiclePayload({
    name: "내 첫 차량",
    vehicle_type: setupForm.vehicle_type,
    fuel_type: setupForm.fuel_type,
    fuel_efficiency_kmpl: DEFAULT_EFFICIENCY,
  });
  await addVehicle(payload);
}

async function handleSignup() {
  if (loading.value) return;

  loading.value = true;
  error.value = null;
  vehicleWarning.value = "";

  try {
    const payload = await signupAccount(signupForm);
    try {
      await createDefaultVehicle();
      clearDraft();
    } catch (vehicleError) {
      vehicleWarning.value = readableError(
        vehicleError,
        "가입은 완료됐지만 차량 기본값은 자동 등록하지 못했습니다. 나의 환경에서 다시 설정해 주세요."
      );
    }
    emit("authenticated", payload.user);
  } catch (err) {
    error.value = err.payload || { message: err.message };
  } finally {
    loading.value = false;
  }
}

onMounted(readDraft);

watch(
  () => ({ fuel_type: setupForm.fuel_type, vehicle_type: setupForm.vehicle_type }),
  writeDraft,
  { deep: true }
);
</script>

<template>
  <main class="onboardingShell">
    <section class="onboardingHero" aria-labelledby="onboarding-title">
      <div class="onboardingLogo">
        <span><Fuel :size="22" /></span>
        <strong>SmartFuel</strong>
      </div>

      <div class="heroCopy">
        <p class="eyebrow">SMART FUEL ROUTINE</p>
        <h1 id="onboarding-title">주유소 선택, 가격만 보지 말고 체감 비용으로 결정하세요.</h1>
        <p>
          SmartFuel은 위치, 이동비, 유가, 카드 할인을 함께 계산해 지금 나에게 맞는 주유 선택을 도와줍니다.
        </p>
      </div>

      <div class="onboardingActions" v-if="mode === 'landing'">
        <button class="primaryButton onboardingPrimary" type="button" @click="startOnboarding">
          처음이에요
          <ArrowRight :size="18" />
        </button>
        <button class="onboardingGhostButton" type="button" @click="emit('login')">
          <LogIn :size="18" />
          로그인
        </button>
      </div>

      <div class="featurePreviewGrid" aria-label="SmartFuel 주요 기능 미리보기">
        <article v-for="feature in featureCards" :key="feature.title" class="featurePreviewCard">
          <div class="featureIcon"><component :is="feature.icon" :size="20" /></div>
          <p>{{ feature.eyebrow }}</p>
          <h2>{{ feature.title }}</h2>
          <span>{{ feature.description }}</span>
        </article>
      </div>
    </section>

    <section v-if="mode === 'onboarding'" class="onboardingSetupCard" aria-labelledby="setup-title">
      <div class="setupIntro">
        <p class="eyebrow">QUICK SETUP</p>
        <h2 id="setup-title">추천에 필요한 기본값만 먼저 알려주세요.</h2>
        <p>집·회사 주소와 카드는 가입 후 나의 환경에서 천천히 추가할 수 있습니다.</p>
      </div>

      <div class="setupPanel">
        <fieldset class="onboardingFieldset">
          <legend>연료 타입</legend>
          <div class="fuelChoiceGrid">
            <label
              v-for="(label, value) in VEHICLE_FUEL_LABELS"
              :key="value"
              class="fuelChoice"
              :class="{ active: setupForm.fuel_type === value }"
            >
              <input v-model="setupForm.fuel_type" type="radio" name="onboarding-fuel" :value="value" />
              <span>{{ label }}</span>
            </label>
          </div>
        </fieldset>

        <fieldset class="onboardingFieldset">
          <legend>차량 유형</legend>
          <VehicleTypePicker v-model="setupForm.vehicle_type" />
        </fieldset>

        <div class="setupSummary">
          <Car :size="20" />
          <div>
            <strong>{{ selectedVehicle.label }} · {{ VEHICLE_FUEL_LABELS[setupForm.fuel_type] }}</strong>
            <span>가입 후 “내 첫 차량”으로 자동 등록됩니다.</span>
          </div>
        </div>
      </div>

      <form class="signupPageCard" @submit.prevent="handleSignup" aria-labelledby="signup-title">
        <div>
          <p class="eyebrow">CREATE ACCOUNT</p>
          <h2 id="signup-title">회원가입</h2>
        </div>

        <label>
          <span>아이디</span>
          <input v-model.trim="signupForm.username" autocomplete="username" required placeholder="사용할 아이디를 입력해 주세요." />
        </label>
        <label>
          <span>이메일</span>
          <input v-model.trim="signupForm.email" type="email" autocomplete="email" required placeholder="이메일 주소를 입력해 주세요." />
        </label>
        <label>
          <span>비밀번호</span>
          <input v-model="signupForm.password" type="password" autocomplete="new-password" required placeholder="비밀번호를 입력해 주세요." />
        </label>

        <div v-if="error" class="errorPanel compact" role="alert">
          <strong>{{ error.code || "SIGNUP_FAILED" }}</strong>
          <span>{{ error.message }}</span>
        </div>
        <div v-if="vehicleWarning" class="errorPanel compact warning" role="status">
          <strong>VEHICLE_SETUP_SKIPPED</strong>
          <span>{{ vehicleWarning }}</span>
        </div>

        <button class="primaryButton fullWidth" type="submit" :disabled="loading">
          <UserPlus :size="18" />
          <span>{{ loading ? "가입 처리 중..." : "설정 저장하고 가입하기" }}</span>
        </button>
        <button class="textButton" type="button" @click="emit('login')">
          이미 계정이 있다면 로그인
        </button>
      </form>
    </section>
  </main>
</template>
