<script setup>
import { ref } from "vue";
import { Save, X } from "@lucide/vue";
import { updateMyCard } from "../../api/cards";
import {
  cardsWorkspaceStore,
  markCardsWorkspaceClean,
  markCardsWorkspaceDirty,
} from "../../stores/cardsWorkspaceStore";
import CardPolicyFields from "./CardPolicyFields.vue";
import { cardPayload, validateCardDraft } from "./cardPresentation";

const props = defineProps({
  cardId: { type: [String, Number], required: true },
});

const emit = defineEmits(["cancel", "saved"]);
const loading = ref(false);
const error = ref("");

async function save() {
  const validationMessage = validateCardDraft(cardsWorkspaceStore.editDraft);
  if (validationMessage) {
    error.value = validationMessage;
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    await updateMyCard(props.cardId, cardPayload(cardsWorkspaceStore.editDraft));
    markCardsWorkspaceClean("edit");
    emit("saved");
  } catch (requestError) {
    error.value = requestError.payload?.message || requestError.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <aside class="editCardPanel" aria-labelledby="edit-card-title">
    <div class="editPanelHeader">
      <div>
        <p class="eyebrow">카드 수정</p>
        <h3 id="edit-card-title">{{ cardsWorkspaceStore.editDraft.card_name }}</h3>
      </div>
      <button class="cardsCloseButton" type="button" aria-label="수정 취소" @click="$emit('cancel')">
        <X :size="18" />
      </button>
    </div>
    <form class="editPanelForm" @submit.prevent="save">
      <div class="cardFormGrid" @input="markCardsWorkspaceDirty('edit')">
        <label>
          <span>카드사</span>
          <input v-model.trim="cardsWorkspaceStore.editDraft.issuer_name" required />
        </label>
        <label>
          <span>카드명</span>
          <input v-model.trim="cardsWorkspaceStore.editDraft.card_name" required />
        </label>
      </div>
      <CardPolicyFields
        :draft="cardsWorkspaceStore.editDraft"
        @dirty="markCardsWorkspaceDirty('edit')"
      />
      <label class="memoField">
        <span>메모 <small>(선택)</small></span>
        <textarea v-model.trim="cardsWorkspaceStore.editDraft.user_memo" rows="3" @input="markCardsWorkspaceDirty('edit')" />
      </label>
      <p v-if="error" class="cardError" role="alert">{{ error }}</p>
      <div class="editPanelActions">
        <button class="cardSecondaryButton" type="button" :disabled="loading" @click="$emit('cancel')">취소</button>
        <button class="cardPrimaryButton" type="submit" :disabled="loading">
          <Save :size="18" />
          {{ loading ? "저장 중…" : "변경 내용 저장" }}
        </button>
      </div>
    </form>
  </aside>
</template>
