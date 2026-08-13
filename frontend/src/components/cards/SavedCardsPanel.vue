<script setup>
import { nextTick, ref } from "vue";
import { Pencil, Plus, Trash2 } from "@lucide/vue";
import { deleteMyCard } from "../../api/cards";
import { cardsWorkspaceStore, markCardsWorkspaceClean } from "../../stores/cardsWorkspaceStore";
import CardArtwork from "./CardArtwork.vue";
import DeleteCardDialog from "./DeleteCardDialog.vue";
import EditCardPanel from "./EditCardPanel.vue";
import { brandLabel, discountLabel } from "./cardPresentation";

defineProps({
  cards: { type: Array, default: () => [] },
});
const emit = defineEmits(["changed", "go-manual"]);
const deleting = ref(false);
const message = ref("");
const error = ref("");
const deleteOpener = ref(null);
const savedTitle = ref(null);

function edit(card) {
  if (
    cardsWorkspaceStore.dirtyAreas.edit
    && cardsWorkspaceStore.editingCardId !== null
    && !window.confirm("수정 중인 내용을 버리고 다른 카드를 열까요?")
  ) {
    return;
  }
  cardsWorkspaceStore.editingCardId = card.card_id;
  Object.assign(cardsWorkspaceStore.editDraft, card);
  markCardsWorkspaceClean("edit");
}

function cancelEdit() {
  if (cardsWorkspaceStore.dirtyAreas.edit && !window.confirm("수정 중인 내용을 취소할까요?")) return;
  cardsWorkspaceStore.editingCardId = null;
  markCardsWorkspaceClean("edit");
}

function saved() {
  cardsWorkspaceStore.editingCardId = null;
  message.value = "카드 정보를 수정했습니다.";
  emit("changed");
}

async function confirmDelete() {
  deleting.value = true;
  error.value = "";
  try {
    const deletedCardId = cardsWorkspaceStore.deleteTarget.card_id;
    await deleteMyCard(deletedCardId);
    cardsWorkspaceStore.deleteTarget = null;
    if (cardsWorkspaceStore.editingCardId === deletedCardId) {
      cardsWorkspaceStore.editingCardId = null;
      markCardsWorkspaceClean("edit");
    }
    message.value = "카드를 삭제했습니다.";
    emit("changed");
    await nextTick();
    savedTitle.value?.focus();
  } catch (requestError) {
    error.value = requestError.payload?.message || requestError.message;
  } finally {
    deleting.value = false;
  }
}

function openDelete(card, event) {
  error.value = "";
  deleteOpener.value = event.currentTarget;
  cardsWorkspaceStore.deleteTarget = card;
}

async function closeDelete() {
  cardsWorkspaceStore.deleteTarget = null;
  await nextTick();
  deleteOpener.value?.focus();
}

function handleSavedPanelKeydown(event) {
  if (event.key !== "Escape" || !cardsWorkspaceStore.editingCardId || cardsWorkspaceStore.deleteTarget) return;
  event.stopPropagation();
  event.preventDefault();
  cancelEdit();
}
</script>

<template>
  <section class="cardsPanel savedPanel" aria-labelledby="saved-title" @keydown="handleSavedPanelKeydown">
    <div class="cardsSectionHeading savedHeading">
      <div>
        <p class="eyebrow">내 카드</p>
        <h3 id="saved-title" ref="savedTitle" tabindex="-1">등록한 카드 {{ cards.length }}개</h3>
        <p>추천 계산에 사용할 주유 혜택을 확인하고 관리하세요.</p>
      </div>
      <button data-card-initial-focus class="cardSecondaryButton" type="button" @click="$emit('go-manual')">
        <Plus :size="18" />
        직접 등록
      </button>
    </div>
    <p v-if="message" class="cardStatus" role="status">{{ message }}</p>
    <p v-if="error" class="cardError" role="alert">{{ error }}</p>

    <div class="savedCardsLayout" :class="{ editing: cardsWorkspaceStore.editingCardId }">
      <div class="savedCardList">
        <article v-for="card in cards" :key="card.card_id" class="savedCardItem">
          <CardArtwork :src="card.card_image_url" :alt="card.card_name" />
          <div class="savedCardMain">
            <span>{{ card.issuer_name }}</span>
            <strong>{{ card.card_name }}</strong>
            <p>{{ discountLabel(card) }} · {{ brandLabel(card.brand_scope) }}</p>
          </div>
          <div class="savedCardActions">
            <button class="cardIconButton" type="button" :aria-label="`${card.card_name} 수정`" @click="edit(card)">
              <Pencil :size="18" />
            </button>
            <button class="cardIconButton danger" type="button" :aria-label="`${card.card_name} 삭제`" @click="openDelete(card, $event)">
              <Trash2 :size="18" />
            </button>
          </div>
        </article>
        <div v-if="!cards.length" class="cardsEmptyState">
          <strong>아직 등록한 카드가 없어요</strong>
          <span>카드를 검색하거나 직접 등록하면 주유비 추천에 반영됩니다.</span>
          <button class="cardPrimaryButton" type="button" @click="$emit('go-manual')">첫 카드 등록하기</button>
        </div>
      </div>

      <EditCardPanel
        v-if="cardsWorkspaceStore.editingCardId"
        :card-id="cardsWorkspaceStore.editingCardId"
        @cancel="cancelEdit"
        @saved="saved"
      />
    </div>

    <DeleteCardDialog
      v-if="cardsWorkspaceStore.deleteTarget"
      :card="cardsWorkspaceStore.deleteTarget"
      :loading="deleting"
      :error="error"
      @cancel="closeDelete"
      @confirm="confirmDelete"
    />
  </section>
</template>
