<script setup>
import { onBeforeUnmount, reactive, ref, watch } from "vue";
import { Save, X } from "@lucide/vue";
import { updateMyCard } from "../../api/cards";
import {
  cardsWorkspaceStore,
  createCardDraftCopy,
  markCardsWorkspaceClean,
  markCardsWorkspaceDirty,
  replaceCardDraft,
} from "../../stores/cardsWorkspaceStore";
import CardPolicyFields from "./CardPolicyFields.vue";
import { cardPayload, validateCardDraft } from "./cardPresentation";

const props = defineProps({
  cardId: { type: [String, Number], required: true },
});

const emit = defineEmits(["cancel", "saved"]);
const loading = ref(false);
const error = ref("");
const editDraft = reactive(createCardDraftCopy(cardsWorkspaceStore.editDraft));

watch(
  () => props.cardId,
  () => {
    replaceCardDraft(editDraft, cardsWorkspaceStore.editDraft);
  },
);

function markDirty() {
  if (!cardsWorkspaceStore.dirtyAreas.edit) {
    markCardsWorkspaceDirty("edit");
  }
}

function persistEditDraft() {
  if (cardsWorkspaceStore.dirtyAreas.edit) {
    replaceCardDraft(cardsWorkspaceStore.editDraft, editDraft);
  }
}

async function save() {
  const validationMessage = validateCardDraft(editDraft);
  if (validationMessage) {
    error.value = validationMessage;
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    await updateMyCard(props.cardId, cardPayload(editDraft));
    replaceCardDraft(cardsWorkspaceStore.editDraft, editDraft);
    markCardsWorkspaceClean("edit");
    emit("saved");
  } catch (requestError) {
    error.value = requestError.payload?.message || requestError.message;
  } finally {
    loading.value = false;
  }
}

onBeforeUnmount(persistEditDraft);
</script>

<template>
  <aside class="editCardPanel" aria-labelledby="edit-card-title">
    <div class="editPanelHeader">
      <div>
        <p class="eyebrow">카드 수정</p>
        <h3 id="edit-card-title">{{ editDraft.card_name }}</h3>
      </div>
      <button class="cardsCloseButton" type="button" aria-label="수정 취소" @click="$emit('cancel')">
        <X :size="18" />
      </button>
    </div>
    <form class="editPanelForm" @submit.prevent="save">
      <div class="cardFormGrid" @input="markDirty">
        <label>
          <span>카드사</span>
          <input v-model.trim="editDraft.issuer_name" required />
        </label>
        <label>
          <span>카드명</span>
          <input v-model.trim="editDraft.card_name" required />
        </label>
      </div>
      <CardPolicyFields
        :draft="editDraft"
        @dirty="markDirty"
      />
      <label class="memoField">
        <span>메모 <small>선택</small></span>
        <textarea v-model.trim="editDraft.user_memo" rows="3" @input="markDirty" />
      </label>
      <p v-if="error" class="cardError" role="alert">{{ error }}</p>
      <div class="editPanelActions">
        <button class="cardSecondaryButton" type="button" :disabled="loading" @click="$emit('cancel')">취소</button>
        <button class="cardPrimaryButton" type="submit" :disabled="loading">
          <Save :size="18" />
          {{ loading ? "저장 중..." : "변경 내용 저장" }}
        </button>
      </div>
    </form>
  </aside>
</template>
