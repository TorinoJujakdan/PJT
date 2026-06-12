<script setup>
import { VEHICLE_TYPES } from "./vehiclePresentation";

defineProps({
  modelValue: {
    type: String,
    required: true
  },
  compact: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(["update:modelValue"]);
</script>

<template>
  <div class="typePicker" :class="{ compact }" role="radiogroup" aria-label="차량 유형">
    <button
      v-for="type in VEHICLE_TYPES"
      :key="type.value"
      class="typeOption"
      :class="{ selected: modelValue === type.value }"
      type="button"
      role="radio"
      :aria-checked="modelValue === type.value"
      @click="emit('update:modelValue', type.value)"
    >
      <img :src="type.imageUrl" alt="" aria-hidden="true" />
      <span class="typeCopy">
        <strong>{{ type.label }}</strong>
        <small v-if="!compact">{{ type.description }}</small>
      </span>
    </button>
  </div>
</template>

<style scoped>
.typePicker {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.typeOption {
  min-width: 0;
  padding: 12px;
  border: 1px solid #d9e2ec;
  border-radius: 14px;
  background: #fff;
  color: #102a43;
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  text-align: left;
  cursor: pointer;
  transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
}

.typeOption:hover {
  border-color: #7dd3fc;
  transform: translateY(-1px);
}

.typeOption:focus-visible {
  outline: 3px solid rgba(14, 165, 233, 0.3);
  outline-offset: 2px;
}

.typeOption.selected {
  border-color: #0284c7;
  background: #f0f9ff;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.12);
}

.typeOption img {
  width: 100%;
  height: 44px;
  object-fit: contain;
  color: #0f172a;
}

.typeCopy {
  display: grid;
  gap: 3px;
}

.typeCopy strong {
  font-size: 13px;
  word-break: keep-all;
}

.typeCopy small {
  color: #627d98;
  font-size: 11px;
  line-height: 1.35;
  word-break: keep-all;
}

.compact {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.compact .typeOption {
  grid-template-columns: 1fr;
  justify-items: center;
  padding: 8px;
  text-align: center;
}

.compact .typeOption img {
  height: 30px;
}

@media (max-width: 560px) {
  .typePicker,
  .compact {
    grid-template-columns: 1fr;
  }
}
</style>
