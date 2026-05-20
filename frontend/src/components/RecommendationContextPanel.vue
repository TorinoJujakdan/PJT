<script setup>
import { Car, CreditCard, Settings } from "@lucide/vue";

defineProps({
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

const fuelLabels = {
  gasoline: "Gasoline",
  diesel: "Diesel",
  lpg: "LPG",
  premium_gasoline: "Premium gasoline"
};
</script>

<template>
  <section class="panel contextPanel">
    <div class="panelHeader">
      <div>
        <p class="eyebrow">Context</p>
        <h2>Your setup</h2>
      </div>
      <Settings :size="20" />
    </div>

    <div v-if="isAuthenticated" class="contextGrid">
      <article class="contextItem">
        <div class="contextIcon">
          <Car :size="18" />
        </div>
        <div>
          <strong>{{ savedVehicle ? fuelLabels[savedVehicle.fuel_type] || savedVehicle.fuel_type : "No saved vehicle" }}</strong>
          <span>
            {{
              savedVehicle && useSavedVehicle
                ? `${savedVehicle.fuel_efficiency_kmpl} km/L will be used by the backend`
                : savedVehicle
                  ? "Manual efficiency is active for this quote"
                  : "Add a vehicle to skip manual efficiency entry"
            }}
          </span>
        </div>
        <button class="iconButton" type="button" title="Vehicle settings" @click="emit('go-vehicle')">
          <Settings :size="17" />
        </button>
      </article>

      <article class="contextItem">
        <div class="contextIcon">
          <CreditCard :size="18" />
        </div>
        <div>
          <strong>{{ savedCards.length }} active card{{ savedCards.length === 1 ? "" : "s" }}</strong>
          <span>Confirmed saved cards are included by the backend.</span>
        </div>
        <button class="iconButton" type="button" title="Card settings" @click="emit('go-cards')">
          <Settings :size="17" />
        </button>
      </article>
    </div>

    <p v-else class="summaryText">
      Anonymous quotes use the vehicle efficiency entered below. Sign in to reuse saved vehicle and card settings.
    </p>
  </section>
</template>
