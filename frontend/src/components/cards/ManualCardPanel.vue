<script setup>
import { ref } from "vue";
import { Plus } from "@lucide/vue";
import { createMyCard } from "../../api/cards";
import {
  blankCardDraft,
  cardsWorkspaceStore,
  markCardsWorkspaceClean,
  markCardsWorkspaceDirty,
} from "../../stores/cardsWorkspaceStore";
import CardPolicyFields from "./CardPolicyFields.vue";
import { cardPayload, validateCardDraft } from "./cardPresentation";

const emit = defineEmits(["changed"]);
const loading = ref(false);
const error = ref("");
const success = ref("");

function markDirty() {
  markCardsWorkspaceDirty("manual");
  success.value = "";
}

async function submit() {
  const validationMessage = validateCardDraft(cardsWorkspaceStore.manualDraft);
  if (validationMessage) {
    error.value = validationMessage;
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    await createMyCard(cardPayload(cardsWorkspaceStore.manualDraft));
    Object.assign(cardsWorkspaceStore.manualDraft, blankCardDraft);
    markCardsWorkspaceClean("manual");
    success.value = "카드를 등록했습니다. 내 카드 탭에서 확인할 수 있어요.";
    emit("changed");
  } catch (requestError) {
    error.value = requestError.payload?.message || requestError.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="cardsPanel manualPanel" aria-labelledby="manual-title">
    <div class="cardsSectionHeading">
      <div>
        <p class="eyebrow">직접 등록</p>
        <h3 id="manual-title">검색되지 않는 카드도 등록할 수 있어요</h3>
        <p>먼저 카드명과 핵심 주유 혜택만 입력하세요. 세부 조건은 선택 사항입니다.</p>
      </div>
    </div>

    <form class="manualCardForm" @submit.prevent="submit">
      <fieldset>
        <legend><span>1</span> 기본 정보 <small>필수</small></legend>
        <div class="cardFormGrid twoColumns" @input="markDirty">
          <label>
            <span>카드사</span>
            <input data-card-initial-focus v-model.trim="cardsWorkspaceStore.manualDraft.issuer_name" required placeholder="예: 신한카드" autocomplete="organization" />
          </label>
          <label>
            <span>카드명</span>
            <input v-model.trim="cardsWorkspaceStore.manualDraft.card_name" required placeholder="예: Deep Oil" />
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend><span>2</span> 주유 혜택 <small>필수</small></legend>
        <CardPolicyFields
          :draft="cardsWorkspaceStore.manualDraft"
          :advanced="false"
          @dirty="markDirty"
        />
      </fieldset>

      <details class="manualAdvanced">
        <summary>세부 이용 조건 입력 <small>선택</small></summary>
        <div class="cardFormGrid twoColumns" @input="markDirty">
          <label>
            <span>최소 결제 금액 <small>(원)</small></span>
            <input v-model.number="cardsWorkspaceStore.manualDraft.min_payment_amount" type="number" min="0" step="1000" />
          </label>
          <label>
            <span>건당 최대 할인 <small>(원)</small></span>
            <input v-model.number="cardsWorkspaceStore.manualDraft.max_discount_amount" type="number" min="0" step="1000" />
          </label>
          <label>
            <span>월 할인 한도 <small>(원)</small></span>
            <input v-model.number="cardsWorkspaceStore.manualDraft.monthly_discount_limit" type="number" min="0" step="1000" />
          </label>
          <label>
            <span>이번 달 남은 한도 <small>(원)</small></span>
            <input v-model.number="cardsWorkspaceStore.manualDraft.monthly_remaining_discount" type="number" min="0" step="1000" />
          </label>
        </div>
      </details>

      <p class="formHint">직접 등록한 혜택은 사용자가 확인한 정보로 저장됩니다.</p>
      <p v-if="error" class="cardError" role="alert">{{ error }}</p>
      <p v-if="success" class="cardStatus" role="status">{{ success }}</p>
      <button class="cardPrimaryButton manualSubmitButton" type="submit" :disabled="loading">
        <Plus :size="19" />
        {{ loading ? "등록 중…" : "내 카드로 등록" }}
      </button>
    </form>
  </section>
</template>
