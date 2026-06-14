<script setup>
import { computed } from "vue";
import { Car, CreditCard, Settings } from "@lucide/vue";
import { getVehiclePresentation, VEHICLE_FUEL_LABELS } from "./vehicles/vehiclePresentation";

const props = defineProps({
  isAuthenticated: {
    type: Boolean,
    default: false
  },
  savedVehicle: {
    type: Object,
    default: null
  },
  savedCards: {
    type: Array,
    default: () => []
  },
  useSavedVehicle: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(["go-vehicle", "go-cards"]);
const vehiclePresentation = computed(() => getVehiclePresentation(props.savedVehicle?.vehicle_type));

const fuelLabels = VEHICLE_FUEL_LABELS;
</script>

<template>
  <section class="panel contextPanel">
    <div class="panelHeader">
      <div>
        <p class="eyebrow">MY SETTINGS</p>
        <h2>현재 적용 설정</h2>
      </div>
      <Settings :size="20" />
    </div>

    <div v-if="isAuthenticated" class="contextGrid">
      <article class="contextItem">
        <div class="contextIcon">
          <img v-if="savedVehicle" :src="vehiclePresentation.imageUrl" alt="" />
          <Car v-else :size="18" />
        </div>
        <div>
          <strong>{{ savedVehicle ? savedVehicle.name : "등록 차량 없음" }}</strong>
          <span>
            {{
              savedVehicle && useSavedVehicle
                ? `${vehiclePresentation.label} · ${fuelLabels[savedVehicle.fuel_type] || savedVehicle.fuel_type} · ${savedVehicle.fuel_efficiency_kmpl} km/L`
                : savedVehicle
                  ? "이번 추천에는 직접 입력한 연비를 적용합니다"
                  : "차량을 등록하면 연비를 다시 입력하지 않아도 됩니다"
            }}
          </span>
        </div>
        <button class="iconButton" type="button" title="차량 설정" aria-label="차량 설정 열기" @click="emit('go-vehicle')">
          <Settings :size="17" />
        </button>
      </article>

      <article class="contextItem">
        <div class="contextIcon">
          <CreditCard :size="18" />
        </div>
        <div>
          <strong>적용 카드 {{ savedCards.length }}개</strong>
          <span>등록한 할인 카드가 추천 비용 계산에 반영됩니다.</span>
        </div>
        <button class="iconButton" type="button" title="카드 설정" aria-label="카드 설정 열기" @click="emit('go-cards')">
          <Settings :size="17" />
        </button>
      </article>
    </div>

    <p v-else class="summaryText">
      로그인하면 저장한 차량 연비와 할인 카드를 추천 조건에 바로 적용할 수 있습니다.
    </p>
  </section>
</template>
