<script setup>
import { computed, ref } from "vue";
import { ArrowLeft, Check, ExternalLink, Search } from "@lucide/vue";
import { createMyCardFromCatalog, searchCardCatalog } from "../../api/cards";
import {
  cardsWorkspaceStore,
  markCardsWorkspaceClean,
  markCardsWorkspaceDirty,
} from "../../stores/cardsWorkspaceStore";
import CardArtwork from "./CardArtwork.vue";
import CardPolicyFields from "./CardPolicyFields.vue";
import {
  brandLabel,
  catalogCardDraft,
  catalogCardPayload,
  discountLabel,
  fuelBenefitStatusLabel,
  manualBenefitNotice,
  requiresManualBenefitEntry,
  trustDisclosure,
  validateCardDraft,
  wonLabel,
} from "./cardPresentation";

const emit = defineEmits(["changed"]);
const loading = ref(false);
const saving = ref(false);
const message = ref("");
const error = ref("");

async function search() {
  loading.value = true;
  error.value = "";
  message.value = "";
  try {
    const payload = await searchCardCatalog({ query: cardsWorkspaceStore.catalogQuery });
    cardsWorkspaceStore.catalogCards = payload.cards || [];
    message.value = cardsWorkspaceStore.catalogCards.length
      ? `${cardsWorkspaceStore.catalogCards.length}개의 카드를 찾았어요.`
      : "검색 결과가 없습니다. 카드명이나 카드사를 바꿔 검색해 보세요.";
  } catch (requestError) {
    error.value = requestError.payload?.message || requestError.message;
  } finally {
    loading.value = false;
  }
}

function selectCard(card) {
  if (
    cardsWorkspaceStore.dirtyAreas.catalog
    && cardsWorkspaceStore.selectedCatalogCard?.catalog_card_id !== card.catalog_card_id
    && !window.confirm("조정 중인 혜택 조건을 버리고 다른 카드를 볼까요?")
  ) return;
  cardsWorkspaceStore.selectedCatalogCard = card;
  Object.assign(
    cardsWorkspaceStore.catalogDraft,
    catalogCardDraft(card),
  );
  error.value = "";
}

function clearSelection() {
  if (
    cardsWorkspaceStore.dirtyAreas.catalog
    && !window.confirm("조정 중인 혜택 조건을 버리고 검색 결과로 돌아갈까요?")
  ) return;
  cardsWorkspaceStore.selectedCatalogCard = null;
  markCardsWorkspaceClean("catalog");
}

async function save() {
  saving.value = true;
  error.value = "";
  const draft = cardsWorkspaceStore.catalogDraft;
  const validationError = validateCardDraft(draft);
  if (validationError) {
    error.value = validationError;
    saving.value = false;
    return;
  }
  try {
    await createMyCardFromCatalog(catalogCardPayload(draft));
    cardsWorkspaceStore.selectedCatalogCard = null;
    markCardsWorkspaceClean("catalog");
    message.value = "카드를 등록했습니다. 내 카드 탭에서 확인할 수 있어요.";
    emit("changed");
  } catch (requestError) {
    error.value = requestError.payload?.message || requestError.message;
  } finally {
    saving.value = false;
  }
}


const selectedRequiresManualEntry = computed(() => (
  requiresManualBenefitEntry(cardsWorkspaceStore.selectedCatalogCard)
));
const selectedManualNotice = computed(() => manualBenefitNotice(cardsWorkspaceStore.selectedCatalogCard));
const selectedStatusLabel = computed(() => fuelBenefitStatusLabel(cardsWorkspaceStore.selectedCatalogCard));

const trust = (card) => trustDisclosure(card);
</script>

<template>
  <section class="cardsPanel" aria-labelledby="catalog-title">
    <template v-if="!cardsWorkspaceStore.selectedCatalogCard">
      <div class="cardsSectionHeading">
        <div>
          <p class="eyebrow">카드 검색</p>
          <h3 id="catalog-title">내 카드를 찾아보세요</h3>
          <p>검색 결과에는 구분하기 쉬운 핵심 정보만 보여드려요.</p>
        </div>
      </div>

      <form class="cardSearchBar" role="search" @submit.prevent="search">
        <label class="srOnly" for="catalog-query">카드명 또는 카드사 검색</label>
        <Search :size="20" aria-hidden="true" />
        <input
          id="catalog-query"
          data-card-initial-focus
          v-model.trim="cardsWorkspaceStore.catalogQuery"
          placeholder="예: 신한 Deep Oil, KB국민"
          autocomplete="off"
        />
        <button class="cardPrimaryButton" type="submit" :disabled="loading">
          {{ loading ? "검색 중…" : "검색" }}
        </button>
      </form>

      <p v-if="message" class="cardStatus" role="status">{{ message }}</p>
      <p v-if="error" class="cardError" role="alert">{{ error }}</p>

      <div v-if="cardsWorkspaceStore.catalogCards.length" class="catalogGrid">
        <button
          v-for="card in cardsWorkspaceStore.catalogCards"
          :key="card.catalog_card_id"
          class="catalogResultCard"
          type="button"
          @click="selectCard(card)"
        >
          <CardArtwork :src="card.card_image_url" :alt="card.card_name" />
          <span class="catalogCardIssuer">{{ card.issuer_name }}</span>
          <strong>{{ card.card_name }}</strong>
          <span class="catalogCardAction">주유 혜택 보기</span>
        </button>
      </div>

      <div v-else-if="!loading" class="cardsEmptyState">
        <Search :size="34" />
        <strong>카드명이나 카드사를 검색해 주세요</strong>
        <span>검색 후 카드 이미지, 카드사, 카드명을 한눈에 비교할 수 있어요.</span>
      </div>
    </template>

    <template v-else>
      <button data-card-initial-focus class="cardBackButton" type="button" @click="clearSelection">
        <ArrowLeft :size="18" />
        검색 결과로
      </button>
      <div class="catalogDetailLayout">
        <div class="catalogDetailIdentity">
          <CardArtwork
            :src="cardsWorkspaceStore.selectedCatalogCard.card_image_url"
            :alt="cardsWorkspaceStore.selectedCatalogCard.card_name"
          />
          <p>{{ cardsWorkspaceStore.selectedCatalogCard.issuer_name }}</p>
          <h3>{{ cardsWorkspaceStore.selectedCatalogCard.card_name }}</h3>
          <p>{{ cardsWorkspaceStore.selectedCatalogCard.raw_summary || "등록된 주유 혜택 정보를 확인해 주세요." }}</p>
        </div>

        <div class="catalogBenefitCard">
          <p class="eyebrow">주유 혜택</p>
          <p v-if="selectedRequiresManualEntry" class="benefitStatusBadge">{{ selectedStatusLabel }}</p>
          <strong class="benefitHeadline" :data-manual-required="selectedRequiresManualEntry">{{ discountLabel(cardsWorkspaceStore.catalogDraft) }}</strong>
          <p v-if="selectedRequiresManualEntry" class="manualBenefitCopy">{{ selectedManualNotice }}</p>
          <dl class="benefitFacts">
            <div><dt>적용 주유소</dt><dd>{{ brandLabel(cardsWorkspaceStore.catalogDraft.brand_scope) }}</dd></div>
            <div><dt>최소 결제</dt><dd>{{ wonLabel(cardsWorkspaceStore.catalogDraft.min_payment_amount) }}</dd></div>
            <div><dt>월 할인 한도</dt><dd>{{ wonLabel(cardsWorkspaceStore.catalogDraft.monthly_discount_limit) }}</dd></div>
          </dl>

          <div class="trustNotice" :data-tone="trust(cardsWorkspaceStore.selectedCatalogCard).tone">
            <strong>{{ trust(cardsWorkspaceStore.selectedCatalogCard).title }}</strong>
            <span>{{ trust(cardsWorkspaceStore.selectedCatalogCard).description }}</span>
            <a
              v-if="cardsWorkspaceStore.selectedCatalogCard.source_url"
              :href="cardsWorkspaceStore.selectedCatalogCard.source_url"
              target="_blank"
              rel="noreferrer"
            >
              혜택 출처 열기 <ExternalLink :size="14" />
            </a>
          </div>

          <details class="benefitAdjustments" :open="selectedRequiresManualEntry">
            <summary>{{ selectedRequiresManualEntry ? "직접 확인한 주유 조건 입력하기" : "내가 확인한 조건으로 조정하기" }}</summary>
            <CardPolicyFields
              :draft="cardsWorkspaceStore.catalogDraft"
              @dirty="markCardsWorkspaceDirty('catalog')"
            />
          </details>

          <p v-if="error" class="cardError" role="alert">{{ error }}</p>
          <button class="cardPrimaryButton cardRegisterButton" type="button" :disabled="saving" @click="save">
            <Check :size="19" />
            {{ saving ? "등록 중" : selectedRequiresManualEntry ? "입력한 조건으로 등록" : "이 혜택으로 바로 등록" }}
          </button>
        </div>
      </div>
    </template>
  </section>
</template>
