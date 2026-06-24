<script setup>
import { computed, reactive, ref } from "vue";
import {
  ArrowRight,
  Car,
  CreditCard,
  Fuel,
  LogIn,
  MapPin,
  UserPlus,
  Users,
} from "@lucide/vue";

import { signupAndAuthenticate } from "../api/accounts";

const emit = defineEmits(["login", "authenticated"]);

const loading = ref(false);
const error = ref(null);

const signupForm = reactive({
  username: "",
  email: "",
  password: "",
});

const copy = {
  navLabel: "SmartFuel \uc2dc\uc791 \uba54\ub274",
  heroA11y: "SmartFuel \uc2e4\uc81c \ucd94\ucc9c \ud654\uba74 \ubbf8\ub9ac\ubcf4\uae30",
  heroTitleFirst: "\uc8fc\uc720\uc18c \uc120\ud0dd\uc744",
  heroTitleAccent: "\uc2e4\uc81c \uc9c0\ucd9c \uae30\uc900",
  heroTitleLast: "\uc73c\ub85c \ubc14\uafb8\uc138\uc694.",
  heroDescription:
    "SmartFuel\uc740 \uc8fc\uc720 \uac00\uaca9, \uc774\ub3d9 \uac70\ub9ac, \ub0b4 \ucc28\ub7c9 \uc5f0\ube44, \ub0b4\uce74\ub4dc\uc758 \uc8fc\uc720 \ud61c\ud0dd\uc744 \ud55c\ubc88\uc5d0 \ube44\uad50\ud574 \uc0ac\uc6a9\uc790\uc758 \ud569\ub9ac\uc801\uc778 \uc8fc\uc720 \uacb0\uc815\uc744 \ub3d5\uc2b5\ub2c8\ub2e4.",
  signupStart: "\ud68c\uc6d0\uac00\uc785\uc73c\ub85c \uc2dc\uc791\ud558\uae30",
  login: "\ub85c\uadf8\uc778\ud558\uae30",
  previewLabel: "SmartFuel \ud654\uba74 \uc608\uc2dc",
  previewTitle: "\uc870\uac74 \uc124\uc815 \u2192 \ucd5c\uc801 \uc8fc\uc720\uc18c",
  conditionLabel: "\ucd94\ucc9c \uc870\uac74",
  conditionTitle: "\ub0b4 \uc870\uac74 \uc785\ub825",
  currentLocation: "\ucd9c\ubc1c\uc9c0: \ud604\uc7ac \uc704\uce58",
  fuelAmount: "\ud718\ubc1c\uc720 \u00b7 40L",
  efficiency: "\uc5f0\ube44 12.4km/L",
  cardApplied: "\uc8fc\uc720 \ud560\uc778 \uce74\ub4dc \uc801\uc6a9",
  bestRecommendation: "\ucd5c\uc801 \ucd94\ucc9c",
  stationName: "\ub3c4\uc2ec\uc5d0\ub108\uc9c0 \uc8fc\uc720\uc18c",
  recommendationReason: "\uc8fc\uc720\ube44\u00b7\uc774\ub3d9\uac70\ub9ac\u00b7\uce74\ub4dc \ud61c\ud0dd \uc885\ud569",
  totalCost: "\uc608\uc0c1 \ucd1d \ube44\uc6a9",
  cardDiscount: "\uce74\ub4dc \ud560\uc778",
  savingEffect: "\uc808\uac10 \ud6a8\uacfc",
  effectsA11y: "SmartFuel \uae30\ub300 \ud6a8\uacfc",
  effectsEyebrow: "EXPECTED EFFECTS",
  effectsTitle: "\ub0b4 \uc870\uac74\uc5d0 \ub9de\ub294 \uc8fc\uc720\uc758 \uae30\uc900",
  effectsDescription:
    "\ub2e8\uc21c \ucd5c\uc800\uac00\uac00 \uc544\ub2cc, \uc2e4\uc81c \uc9c0\ucd9c\uc744 \uc904\uc774\ub294 \uc120\ud0dd\uc744 \ub9cc\ub4dc\ub294 \ub370 \uc9d1\uc911\ud588\uc2b5\ub2c8\ub2e4.",
  serviceEyebrow: "SERVICE INTRO",
  serviceTitle: "SmartFuel\uc774 \uc81c\uacf5\ud558\ub294 \uc138 \uac00\uc9c0 \ud575\uc2ec \uae30\ub2a5",
  serviceDescription:
    "\ucd94\ucc9c\uc740 \ubc31\uc5d4\ub4dc \uacc4\uc0b0 \uacb0\uacfc\ub97c \uadf8\ub300\ub85c \ubcf4\uc5ec\uc8fc\uace0, \uc0ac\uc6a9\uc790\ub294 \uacb0\uacfc\ub97c \uc774\ud574\ud558\uace0 \uc800\uc7a5\ub41c \ud658\uacbd\uc744 \uad00\ub9ac\ud558\ub294 \ub370 \uc9d1\uc911\ud569\ub2c8\ub2e4.",
  guideEyebrow: "HOW IT WORKS",
  guideTitle: "\uc0ac\uc6a9 \ud750\ub984 \uc18c\uac1c",
  guideDescription:
    "\uacc4\uc815\uc744 \ub9cc\ub4e0 \ub4a4 \uc815\ubcf4\ub97c \ub4f1\ub85d\ud558\uace0 \uc11c\ube44\uc2a4\ub97c \uc774\uc6a9\ud558\uc138\uc694.",
  signupEyebrow: "START SMARTFUEL",
  signupCopyTitleFirst: "\uc900\ube44\uac00 \ub05d\ub0ac\ub2e4\uba74,",
  signupCopyTitleLast: "\uc774\uc81c \uac00\ubccd\uac8c \uc2dc\uc791\ud574\ubcf4\uc138\uc694.",
  signupCopyDescription:
    "\ubcf5\uc7a1\ud55c \ucd08\uae30 \uc124\uc815 \uc5c6\uc774 \ud544\uc218 \uc815\ubcf4\ub9cc\uc73c\ub85c \ubc14\ub85c \uc11c\ube44\uc2a4\ub97c \uc774\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4. \ub0b4 \ucc28\ub7c9\uacfc \uce74\ub4dc\ub294 \ub098\uc911\uc5d0 \ucc9c\ucc9c\ud788 \ub4f1\ub85d\ud558\uc154\ub3c4 \uad1c\ucc2e\uc544\uc694.",
  vehicleLater: "\ud544\uc218 \uc815\ubcf4\ub9cc\uc73c\ub85c \ube60\ub978 \uac00\uc785",
  cardLater: "\ucc28\ub7c9\u00b7\uce74\ub4dc\ub294 \ub098\uc911\uc5d0 \ub4f1\ub85d",
  enterAfterSignup: "\uac00\uc785 \ud6c4 \ubc14\ub85c \ucd94\ucc9c \ud654\uba74\uc73c\ub85c \uc774\ub3d9",
  signupFormEyebrow: "START SMARTFUEL",
  signupTitle: "\ud68c\uc6d0\uac00\uc785",
  username: "\uc544\uc774\ub514",
  usernamePlaceholder: "\uc0ac\uc6a9\ud560 \uc544\uc774\ub514",
  email: "\uc774\uba54\uc77c",
  password: "\ube44\ubc00\ubc88\ud638",
  passwordPlaceholder: "\ube44\ubc00\ubc88\ud638 \uc785\ub825",
  signupSubmit: "\uacc4\uc815 \ub9cc\ub4e4\uace0 \uc2dc\uc791\ud558\uae30",
  signupLoading: "\uac00\uc785 \ucc98\ub9ac \uc911...",
  alreadyAccount: "\uc774\ubbf8 \uacc4\uc815\uc774 \uc788\ub2e4\uba74 \ub85c\uadf8\uc778",
  signupFailed: "\ud68c\uc6d0\uac00\uc785 \uc694\uccad\uc744 \ucc98\ub9ac\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.",
};

const heroMetrics = [
  { value: "1\ubd84", label: "\uc870\uac74 \uc785\ub825\ubd80\ud130 \ucd94\ucc9c\uae4c\uc9c0" },
  { value: "\ud55c\ubc88 \uc124\uc815", label: "\ucc28\ub7c9\u00b7\uce74\ub4dc \uc800\uc7a5 \ud6c4 \ubc18\ubcf5 \uc0ac\uc6a9" },
  {
    value: "\ucd5c\uc801 \ube44\uc6a9 \ucd94\ucc9c",
    label: "\uc8fc\uc720\ube44, \uc774\ub3d9\uac70\ub9ac, \uce74\ub4dc \ud61c\ud0dd\uc744 \uc885\ud569\ud574 \uac00\uc7a5 \uacbd\uc81c\uc801\uc778 \uc8fc\uc720\uc18c \ucd94\ucc9c",
  },
];

const expectedEffects = [
  {
    icon: Fuel,
    title: "\uc2e4\uc81c \uc9c0\ucd9c\uc5d0 \uac00\uae4c\uc6b4 \uc8fc\uc720 \ud310\ub2e8",
    description: "\ub9ac\ud130\ub2f9 \uac00\uaca9\ub9cc \ubcf4\uc9c0 \uc54a\uace0 \uc774\ub3d9 \ube44\uc6a9\uacfc \uce74\ub4dc \ud61c\ud0dd\uae4c\uc9c0 \ud568\uaed8 \ube44\uad50\ud574 \uccb4\uac10 \ube44\uc6a9\uc744 \ub0ae\ucda5\ub2c8\ub2e4.",
  },
  {
    icon: MapPin,
    title: "\uc9c0\uae08 \uc704\uce58\uc640 \uacbd\ub85c\uc5d0 \ub9de\ucd98 \uc120\ud0dd",
    description: "\ucd9c\ubc1c\uc9c0 \uc8fc\ubcc0 \uc8fc\uc720\uc18c\ub97c \uc9c0\ub3c4\uc640 \ubaa9\ub85d\uc73c\ub85c \ud655\uc778\ud558\uace0, \ucd94\ucc9c \uadfc\uac70\ub97c \ubc14\ub85c \uc774\ud574\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
  },
  {
    icon: CreditCard,
    title: "\ub0b4 \uce74\ub4dc \ud61c\ud0dd\uc744 \ub193\uce58\uc9c0 \uc54a\uae30",
    description: "\ubcf4\uc720 \uce74\ub4dc\uc758 \uc8fc\uc720 \ud560\uc778 \uc870\uac74\uc744 \ub4f1\ub85d\ud574 \ub098\uc758 \ud61c\ud0dd\uc744 \ud65c\uc6a9\ud558\ub3c4\ub85d \ub3d5\uc2b5\ub2c8\ub2e4.",
  },
];

const serviceHighlights = [
  {
    eyebrow: "SMART RECOMMENDATION",
    title: "\ud569\ub9ac\uc801\uc778 \uc8fc\uc720\uc18c \ucd94\ucc9c",
    description: "\uc8fc\uc720 \uac00\uaca9, \uac70\ub9ac, \uc608\uc0c1 \uc774\ub3d9 \ube44\uc6a9\uc744 \uc885\ud569\uc801\uc73c\ub85c \uacc4\uc0b0\ud574 \uac00\uc7a5 \uacbd\uc81c\uc801\uc778 \uc8fc\uc720\uc18c\ub97c \uc548\ub0b4\ud569\ub2c8\ub2e4.",
  },
  {
    eyebrow: "PERSONALIZED PROFILE",
    title: "\ub098\ub9cc\uc758 \ub9de\ucda4 \ud658\uacbd \uc124\uc815",
    description: "\ub0b4 \ucc28\ub7c9\uc758 \uc5f0\ube44\uc640 \ubcf4\uc720 \uc911\uc778 \uce74\ub4dc\uc758 \ud61c\ud0dd\uc744 \ud55c \ubc88\ub9cc \ub4f1\ub85d\ud574\ub450\uba74, \ub9e4\ubc88 \ub098\uc5d0\uac8c \ub531 \ub9de\ub294 \ucd5c\uc801\uc758 \uc8fc\uc720\uc18c\ub97c \uc790\ub3d9\uc73c\ub85c \uacc4\uc0b0\ud574 \uc90d\ub2c8\ub2e4.",
  },
  {
    eyebrow: "COMMUNITY",
    title: "\uc6b4\uc804\uc790 \uc18c\ud1b5 \ucc44\ub110",
    description: "\ub2e4\ub978 \uc6b4\uc804\uc790\ub4e4\uacfc \uac00\ubccd\uac8c \uc8fc\uc720 \uacbd\ud5d8\uc744 \ub098\ub204\uace0 \uce74\ub4dc \ud65c\uc6a9 \ud301 \ub4f1 \uc720\uc6a9\ud55c \uc815\ubcf4\ub97c \uacf5\uc720\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
  },
];

const guideSteps = [
  {
    step: "01",
    icon: CreditCard,
    title: "\ub0b4 \ud658\uacbd\uacfc \ucd94\ucc9c \uae30\uc900 \uc124\uc815",
    description: "\uba3c\uc800 \ub098\uc758 \ud658\uacbd \ud0ed\uc5d0\uc11c \ucc28\ub7c9 \uc5f0\ube44\uc640 \ubcf4\uc720 \uce74\ub4dc \ud61c\ud0dd\uc744 \ub4f1\ub85d\ud558\uace0, \uc120\uc815 \ubc29\uc2dd \ud0ed\uc5d0\uc11c \uc6d0\ud558\ub294 \uc8fc\uc720\uc18c \ucd94\ucc9c \uae30\uc900\uc744 \uc124\uc815\ud569\ub2c8\ub2e4.",
    previewTitle: "\ub098\uc758 \ud658\uacbd \u00b7 \uc120\uc815 \ubc29\uc2dd",
    previewRows: ["\ucc28\ub7c9 \uc5f0\ube44 \ub4f1\ub85d", "\uce74\ub4dc \ud61c\ud0dd \ucd94\uac00", "\ucd94\ucc9c \ubc29\uc2dd \uc120\ud0dd"],
  },
  {
    step: "02",
    icon: MapPin,
    title: "\ucd9c\ubc1c\uc9c0\uc640 \uc8fc\uc720 \uc870\uac74 \uc785\ub825",
    description: "\uc704\uce58 \ud0ed\uc5d0\uc11c \ud604\uc7ac \uc704\uce58\ub098 \uc6d0\ud558\ub294 \ucd9c\ubc1c\uc9c0\ub97c \uc815\ud558\uace0, \uc5f0\ub8cc \uc885\ub958\uc640 \uc8fc\uc720\ub7c9\uc744 \uc785\ub825\ud569\ub2c8\ub2e4. \uc124\uc815\ud55c \ub85c\uc9c1\uc5d0 \ub530\ub77c \uc870\uac74\uc5d0 \ub9de\ub294 \uc8fc\uc720\uc18c\ub97c \ucd94\ucc9c\ubc1b\uc744 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
    previewTitle: "\uc704\uce58\uc640 \uc8fc\uc720 \uc870\uac74",
    previewRows: ["\ucd9c\ubc1c\uc9c0: \ud604\uc7ac \uc704\uce58", "\ud718\ubc1c\uc720 \u00b7 40L", "\ucd5c\uc801 \ube44\uc6a9 \uae30\uc900"],
  },
  {
    step: "03",
    icon: ArrowRight,
    title: "\ucd94\ucc9c \uacb0\uacfc \ud655\uc778\uacfc \uae38\uc548\ub0b4",
    description: "\ucd94\ucc9c\ub41c \uc8fc\uc720\uc18c\uc758 \uc608\uc0c1 \uc9c0\ucd9c\uc561\uacfc \ucd94\ucc9c \uc774\uc720\ub97c \ud655\uc778\ud55c \ub4a4, \ud544\uc694\ud558\uba74 \ub124\uc774\ubc84 \uc9c0\ub3c4\ub85c \uc5f0\uacb0\ud574 \ud574\ub2f9 \uc8fc\uc720\uc18c\uae4c\uc9c0 \ud3b8\ub9ac\ud558\uac8c \uae38\uc548\ub0b4\ub97c \ubc1b\uc2b5\ub2c8\ub2e4.",
    previewTitle: "\ucd94\ucc9c \uacb0\uacfc",
    previewRows: ["\uc608\uc0c1 \ucd1d \ube44\uc6a9 65,500\uc6d0", "\ucd94\ucc9c \uc774\uc720 \ud655\uc778", "\ub124\uc774\ubc84 \uc9c0\ub3c4 \uae38\uc548\ub0b4"],
  },
];

const errorMessage = computed(() => {
  if (!error.value) return "";
  const details = error.value.details;
  if (details && typeof details === "object") {
    const first = Object.entries(details)[0];
    if (first) {
      const [field, messages] = first;
      const message = Array.isArray(messages) ? messages[0] : messages;
      if (message) return `${field}: ${message}`;
    }
  }
  return error.value.message || copy.signupFailed;
});

function scrollToSignup() {
  document.getElementById("onboarding-signup")?.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function handleSignup() {
  if (loading.value) return;

  loading.value = true;
  error.value = null;

  try {
    const payload = await signupAndAuthenticate({
      username: signupForm.username,
      email: signupForm.email,
      password: signupForm.password,
    });
    emit("authenticated", payload.user);
  } catch (err) {
    error.value = err.payload || { message: err.message };
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="onboardingShell onboardingLanding">
    <section class="landingHero" aria-labelledby="onboarding-title">
      <nav class="landingNav" :aria-label="copy.navLabel">
        <div class="onboardingLogo">
          <span><Fuel :size="22" /></span>
          <strong>SmartFuel</strong>
        </div>
      </nav>

      <div class="heroLayout">
        <div class="heroCopy">
          <h1 id="onboarding-title" class="heroTitle">
            <span class="heroTitleSmall">{{ copy.heroTitleFirst }}</span>
            <span class="heroTitleAccent">{{ copy.heroTitleAccent }}</span>
            <span class="heroTitleSmall">{{ copy.heroTitleLast }}</span>
          </h1>
          <p>{{ copy.heroDescription }}</p>
          <div class="onboardingActions">
            <button class="primaryButton onboardingPrimary" type="button" @click="scrollToSignup">
              {{ copy.signupStart }}
              <ArrowRight :size="18" />
            </button>
            <button class="onboardingGhostButton" type="button" @click="emit('login')">
              <LogIn :size="18" />
              {{ copy.login }}
            </button>
          </div>
        </div>

        <aside class="heroShowcase actualPreview" :aria-label="copy.heroA11y">
          <div class="showcaseTopline">
            <span>{{ copy.previewLabel }}</span>
            <strong>{{ copy.previewTitle }}</strong>
          </div>

          <div class="actualPreviewFrame">
            <div class="actualPreviewSidebar">
              <div class="previewPanelTitle">
                <span>{{ copy.conditionLabel }}</span>
                <strong>{{ copy.conditionTitle }}</strong>
              </div>
              <div class="previewField active">
                <MapPin :size="14" />
                <span>{{ copy.currentLocation }}</span>
              </div>
              <div class="previewField">
                <Fuel :size="14" />
                <span>{{ copy.fuelAmount }}</span>
              </div>
              <div class="previewField">
                <Car :size="14" />
                <span>{{ copy.efficiency }}</span>
              </div>
              <div class="previewField">
                <CreditCard :size="14" />
                <span>{{ copy.cardApplied }}</span>
              </div>
            </div>

            <div class="actualPreviewMap">
              <div class="mapToolbar">
                <span></span><span></span><span></span>
              </div>
              <span class="stationMarker best"><MapPin :size="16" /></span>
              <span class="stationMarker candidate one"></span>
              <span class="stationMarker candidate two"></span>
              <div class="routeLine actual"></div>
              <div class="mapResultCard">
                <p>{{ copy.bestRecommendation }}</p>
                <strong>{{ copy.stationName }}</strong>
                <span>{{ copy.recommendationReason }}</span>
              </div>
            </div>
          </div>

          <div class="costGrid actualCostGrid">
            <div><span>{{ copy.totalCost }}</span><strong>65,500&#xC6D0;</strong></div>
            <div><span>{{ copy.cardDiscount }}</span><strong>-3,000&#xC6D0;</strong></div>
            <div><span>{{ copy.savingEffect }}</span><strong>2,400&#xC6D0;</strong></div>
          </div>
        </aside>
      </div>

      <div class="heroMetricGrid" :aria-label="copy.effectsA11y">
        <div v-for="metric in heroMetrics" :key="metric.label" class="heroMetric">
          <strong>{{ metric.value }}</strong>
          <span>{{ metric.label }}</span>
        </div>
      </div>
    </section>

    <section class="landingSection" aria-labelledby="effects-title">
      <div class="sectionHeading centered">
        <h2 id="effects-title">{{ copy.effectsTitle }}</h2>
        <span>{{ copy.effectsDescription }}</span>
      </div>
      <div class="effectGrid">
        <article v-for="effect in expectedEffects" :key="effect.title" class="effectCard">
          <div class="featureIcon"><component :is="effect.icon" :size="21" /></div>
          <h3>{{ effect.title }}</h3>
          <p>{{ effect.description }}</p>
        </article>
      </div>
    </section>

    <section class="landingSection serviceIntro" aria-labelledby="service-title">
      <div class="sectionHeading">
        <h2 id="service-title">{{ copy.serviceTitle }}</h2>
      </div>
      <div class="serviceGrid">
        <article v-for="item in serviceHighlights" :key="item.title" class="serviceCard">
          <p>{{ item.eyebrow }}</p>
          <h3>{{ item.title }}</h3>
          <span>{{ item.description }}</span>
        </article>
      </div>
    </section>

    <section class="landingSection guideSection" aria-labelledby="guide-title">
      <div class="sectionHeading centered">
        <p class="eyebrow">{{ copy.guideEyebrow }}</p>
        <h2 id="guide-title">{{ copy.guideTitle }}</h2>
        <span>{{ copy.guideDescription }}</span>
      </div>
      <div class="guideGrid">
        <article v-for="guide in guideSteps" :key="guide.step" class="guideCard">
          <div class="guideCopy">
            <strong>{{ guide.step }}</strong>
            <h3>{{ guide.title }}</h3>
            <p>{{ guide.description }}</p>
          </div>
          <div class="guideIllustration" :class="`guideIllustrationStep${guide.step}`" aria-hidden="true">
            <div class="guideOrb primary">
              <component :is="guide.icon" :size="30" />
            </div>
            <span class="guideLine"></span>
            <div class="guideOrb soft">
              <Fuel :size="22" />
            </div>
            <div class="guideMiniLabel">{{ guide.previewTitle }}</div>
          </div>
        </article>
      </div>
    </section>

    <section id="onboarding-signup" class="signupLandingSection" aria-labelledby="signup-title">
      <div class="signupCopyPanel">
        <p class="eyebrow">{{ copy.signupEyebrow }}</p>
        <h2>
          <span>{{ copy.signupCopyTitleFirst }}</span>
          <span>{{ copy.signupCopyTitleLast }}</span>
        </h2>
      </div>

      <form class="signupPageCard refined" @submit.prevent="handleSignup" aria-labelledby="signup-title">
        <div>
          <p class="eyebrow">{{ copy.signupFormEyebrow }}</p>
          <h2 id="signup-title">{{ copy.signupTitle }}</h2>
        </div>

        <label>
          <span>{{ copy.username }}</span>
          <input v-model.trim="signupForm.username" autocomplete="username" required :placeholder="copy.usernamePlaceholder" />
        </label>
        <label>
          <span>{{ copy.email }}</span>
          <input v-model.trim="signupForm.email" type="email" autocomplete="email" required placeholder="you@example.com" />
        </label>
        <label>
          <span>{{ copy.password }}</span>
          <input v-model="signupForm.password" type="password" autocomplete="new-password" required :placeholder="copy.passwordPlaceholder" />
        </label>

        <div v-if="error" class="errorPanel compact" role="alert">
          <strong>{{ error.code || "SIGNUP_FAILED" }}</strong>
          <span>{{ errorMessage }}</span>
        </div>

        <button class="primaryButton fullWidth" type="submit" :disabled="loading">
          <UserPlus :size="18" />
          <span>{{ loading ? copy.signupLoading : copy.signupSubmit }}</span>
        </button>
        <button class="textButton" type="button" @click="emit('login')">
          {{ copy.alreadyAccount }}
        </button>
      </form>
    </section>
  </main>
</template>

