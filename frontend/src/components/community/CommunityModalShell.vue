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
  (dialog.value?.querySelector("[data-community-initial-focus]") || focusableElements()[0] || dialog.value)?.focus();
});

onBeforeUnmount(() => {
  document.body.classList.remove("modalOpen");
});
</script>

<template>
  <div class="cardsModalOverlay" @mousedown.self="emit('close')">
    <section
      ref="dialog"
      class="cardsModalShell communityModalShell"
      role="dialog"
      aria-modal="true"
      aria-labelledby="community-modal-title"
      tabindex="-1"
      @keydown="handleKeydown"
    >
      <header class="cardsModalHeader">
        <div>
          <p class="eyebrow">COMMUNITY</p>
          <h2 id="community-modal-title">커뮤니티</h2>
          <p>주유소 이용 경험을 검색하고 공유하세요. 실방문 인증과 추천 알고리즘 반영은 포함하지 않습니다.</p>
        </div>
        <button class="cardsCloseButton" type="button" aria-label="커뮤니티 닫기" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>
      <div class="cardsModalBody">
        <slot />
      </div>
    </section>
  </div>
</template>
