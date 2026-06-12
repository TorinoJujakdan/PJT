<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { X } from "@lucide/vue";

const emit = defineEmits(["close"]);
const dialog = ref(null);

function focusableElements() {
  if (!dialog.value) return [];
  return [...dialog.value.querySelectorAll(
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )];
}

function handleKeydown(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    emit("close");
    return;
  }
  if (event.key !== "Tab") return;

  const focusables = focusableElements();
  if (!focusables.length) {
    event.preventDefault();
    dialog.value?.focus();
    return;
  }
  const first = focusables[0];
  const last = focusables.at(-1);
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

onMounted(async () => {
  document.body.classList.add("modalOpen");
  await nextTick();
  (focusableElements()[0] || dialog.value)?.focus();
});

onBeforeUnmount(() => {
  document.body.classList.remove("modalOpen");
});
</script>

<template>
  <div class="glassModalOverlay" @mousedown.self="emit('close')">
    <section
      ref="dialog"
      class="glassModalContainer vehicleModalContainer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="vehicle-modal-title"
      tabindex="-1"
      @keydown="handleKeydown"
    >
      <header class="glassModalHeader">
        <h2 id="vehicle-modal-title">내 차량 정보 설정</h2>
        <button class="glassModalCloseBtn" type="button" @click="emit('close')" aria-label="차량 설정 닫기">
          <X :size="16" />
        </button>
      </header>
      <slot />
    </section>
  </div>
</template>
