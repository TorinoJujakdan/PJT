<script setup>
import { nextTick, onMounted, ref } from "vue";
import { AlertTriangle } from "@lucide/vue";

const props = defineProps({
  card: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
});

const emit = defineEmits(["cancel", "confirm"]);
const cancelButton = ref(null);
const dialog = ref(null);

function handleKeydown(event) {
  if (event.key === "Escape" && !props.loading) {
    event.stopPropagation();
    emit("cancel");
    return;
  }
  if (event.key !== "Tab") return;
  const buttons = [...dialog.value.querySelectorAll("button:not([disabled])")];
  if (!buttons.length) {
    event.preventDefault();
    dialog.value.focus();
    return;
  }
  const first = buttons[0];
  const last = buttons.at(-1);
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

onMounted(async () => {
  await nextTick();
  cancelButton.value?.focus();
});
</script>

<template>
  <div class="deleteDialogBackdrop" data-card-subdialog @keydown="handleKeydown">
    <section
      ref="dialog"
      class="deleteDialog"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="delete-card-title"
      aria-describedby="delete-card-description"
      tabindex="-1"
    >
      <AlertTriangle :size="28" aria-hidden="true" />
      <h3 id="delete-card-title">이 카드를 삭제할까요?</h3>
      <p id="delete-card-description">
        <strong>{{ card.issuer_name }} {{ card.card_name }}</strong> 카드가 추천 계산에서 제외됩니다.
      </p>
      <p v-if="error" class="cardError" role="alert">{{ error }}</p>
      <div class="deleteDialogActions">
        <button ref="cancelButton" class="cardSecondaryButton" type="button" :disabled="loading" @click="$emit('cancel')">
          취소
        </button>
        <button class="cardDangerButton" type="button" :disabled="loading" @click="$emit('confirm')">
          {{ loading ? "삭제 중…" : "삭제" }}
        </button>
      </div>
    </section>
  </div>
</template>
