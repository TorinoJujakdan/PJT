<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { X } from "@lucide/vue";
import { cardsWorkspaceStore, resetCardsWorkspace } from "../../stores/cardsWorkspaceStore";

const emit = defineEmits(["close"]);
const dialog = ref(null);

function focusableElements() {
  if (!dialog.value) return [];
  return [...dialog.value.querySelectorAll(
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )];
}

function requestClose() {
  if (cardsWorkspaceStore.isDirty) {
    if (!window.confirm("작성 중인 카드 정보가 있습니다. 내용을 버리고 닫을까요?")) return;
    resetCardsWorkspace();
  }
  emit("close");
}

function handleKeydown(event) {
  if (event.key === "Escape") {
    if (dialog.value?.querySelector("[data-card-subdialog]")) return;
    event.preventDefault();
    requestClose();
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
  (dialog.value?.querySelector("[data-card-initial-focus]") || focusableElements()[0] || dialog.value)?.focus();
});

onBeforeUnmount(() => {
  document.body.classList.remove("modalOpen");
});
</script>

<template>
  <div class="cardsModalOverlay" @mousedown.self="requestClose">
    <section
      ref="dialog"
      class="cardsModalShell"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cards-modal-title"
      tabindex="-1"
      @keydown="handleKeydown"
    >
      <header class="cardsModalHeader">
        <div>
          <p class="eyebrow">MY FUEL CARD</p>
          <h2 id="cards-modal-title">주유 할인 카드 관리</h2>
          <p>카드를 찾고, 주유 혜택을 확인한 뒤 바로 등록하세요.</p>
        </div>
        <button class="cardsCloseButton" type="button" aria-label="카드 관리 닫기" @click="requestClose">
          <X :size="20" />
        </button>
      </header>
      <div class="cardsModalBody">
        <slot />
      </div>
    </section>
  </div>
</template>
