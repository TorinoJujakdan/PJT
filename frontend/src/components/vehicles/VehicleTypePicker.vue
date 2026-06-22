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

function selectByKeyboard(event, index) {
  const keys = ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"];
  if (!keys.includes(event.key)) return;

  event.preventDefault();
  const options = [...event.currentTarget.parentElement.querySelectorAll('[role="radio"]')];
  const lastIndex = options.length - 1;
  let nextIndex = index;

  if (event.key === "ArrowRight" || event.key === "ArrowDown") nextIndex = index === lastIndex ? 0 : index + 1;
  if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextIndex = index === 0 ? lastIndex : index - 1;
  if (event.key === "Home") nextIndex = 0;
  if (event.key === "End") nextIndex = lastIndex;

  emit("update:modelValue", VEHICLE_TYPES[nextIndex].value);
  options[nextIndex]?.focus();
}
</script>

<template>
  <div class="typePicker" :class="{ compact }" role="radiogroup" aria-label="차량 유형">
    <button
      v-for="(type, index) in VEHICLE_TYPES"
      :key="type.value"
      class="typeOption"
      :class="{ selected: modelValue === type.value }"
      type="button"
      role="radio"
      :aria-checked="modelValue === type.value"
      :tabindex="modelValue === type.value ? 0 : -1"
      @click="emit('update:modelValue', type.value)"
      @keydown="selectByKeyboard($event, index)"
    >
      <img :src="type.imageUrl" alt="" aria-hidden="true" :class="type.imageClass" />
      <strong>{{ type.label }}</strong>
    </button>
  </div>
</template>

<style scoped>
.typePicker {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px 12px;
}

.typeOption {
  min-width: 0;
  padding: 6px 6px 8px;
  border: 2px solid transparent;
  border-radius: 18px;
  background: transparent;
  color: var(--slate-900);
  display: grid;
  gap: 6px;
  text-align: center;
  cursor: pointer;
  transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease, background 160ms ease;
}

.typeOption:hover {
  transform: translateY(-2px);
}

.typeOption:focus-visible {
  outline: 3px solid rgba(15, 107, 79, 0.45);
  outline-offset: 3px;
}

.typeOption.selected {
  border-color: var(--primary);
  background: rgba(15, 107, 79, 0.05);
  box-shadow: 0 0 0 3px rgba(15, 107, 79, 0.1), 0 12px 24px rgba(15, 23, 42, 0.1);
}

.typeOption img {
  display: block;
  width: 100%;
  aspect-ratio: 640 / 394;
  object-fit: contain;
  border-radius: 13px;
}


.typeOption strong {
  padding-inline: 5px;
  color: var(--slate-900);
  font-size: 12px;
  line-height: 1.3;
  word-break: keep-all;
}

.compact {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 9px 7px;
}

.compact .typeOption {
  border-radius: 13px;
}

.compact .typeOption img {
  border-radius: 10px;
}

@media (max-width: 620px) {
  .typePicker {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 9px;
  }

  .compact {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 380px) {
  .typePicker,
  .compact {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (prefers-reduced-motion: reduce) {
  .typeOption {
    transition: none;
  }

  .typeOption:hover {
    transform: none;
  }
}
</style>
