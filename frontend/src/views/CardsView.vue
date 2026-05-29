<script setup>
import { computed, reactive, ref } from "vue";
import { Check, CreditCard, Pencil, Plus, Save, Search, Trash2, X } from "@lucide/vue";
import { createMyCard, createMyCardFromCatalog, deleteMyCard, searchCardCatalog, updateMyCard } from "../api/cards";

defineProps({
  cards: {
    type: Array,
    default: () => []
  }
});
const emit = defineEmits(["changed"]);

const blankForm = {
  card_name: "",
  issuer_name: "",
  discount_type: "per_liter",
  discount_value: 80,
  brand_scope: "all",
  min_payment_amount: null,
  max_discount_amount: null,
  monthly_discount_limit: null,
  monthly_remaining_discount: null
};

const form = reactive({ ...blankForm });
const catalogDraft = reactive({
  catalog_card_id: null,
  card_name: "",
  issuer_name: "",
  discount_type: "per_liter",
  discount_value: 0,
  brand_scope: "all",
  min_payment_amount: null,
  max_discount_amount: null,
  monthly_discount_limit: null,
  monthly_remaining_discount: null,
  user_memo: ""
});

const loading = ref(false);
const catalogLoading = ref(false);
const catalogSaving = ref(false);
const deletingId = ref(null);
const error = ref(null);
const catalogError = ref(null);
const success = ref(false);
const catalogSuccess = ref("");
const catalogQuery = ref("");
const catalogCards = ref([]);
const selectedCatalogCard = ref(null);
const failedImages = ref(new Set());
const editingCardId = ref(null);
const editCardForm = reactive({
  card_name: "",
  issuer_name: "",
  discount_type: "per_liter",
  discount_value: 0,
  brand_scope: "all",
  min_payment_amount: null,
  max_discount_amount: null,
  monthly_discount_limit: null,
  monthly_remaining_discount: null,
  user_memo: ""
});
const editCardError = ref(null);
const editCardLoading = ref(false);

const discountMax = computed(() => (form.discount_type === "percentage" ? 100 : undefined));
const draftDiscountMax = computed(() => (catalogDraft.discount_type === "percentage" ? 100 : undefined));
const editDiscountMax = computed(() => (editCardForm.discount_type === "percentage" ? 100 : undefined));

function discountUnit(type) {
  if (type === "percentage") return "%";
  if (type === "per_liter") return "원/L";
  return "원";
}

function optionalNumber(value) {
  if (value === "" || value === null || value === undefined) return null;
  return Number(value);
}

function validateDiscountPayload(payload) {
  if (!payload.discount_type) return "할인 방식을 선택해 주세요.";
  const discountValue = Number(payload.discount_value);
  if (Number.isNaN(discountValue) || discountValue < 0) return "할인값은 0 이상 숫자로 입력해 주세요.";
  if (payload.discount_type === "percentage" && discountValue > 100) return "비율 할인은 100%를 초과할 수 없습니다.";
  return null;
}

function validateManualForm() {
  if (!form.issuer_name.trim() || !form.card_name.trim()) return "카드사와 카드명을 모두 입력해 주세요.";
  return validateDiscountPayload(form);
}

function resetManualForm() {
  Object.assign(form, blankForm);
}

async function submit() {
  const validationMessage = validateManualForm();
  if (validationMessage) {
    error.value = { message: validationMessage };
    success.value = false;
    return;
  }

  loading.value = true;
  error.value = null;
  success.value = false;
  try {
    await createMyCard({
      ...form,
      discount_value: Number(form.discount_value || 0),
      min_payment_amount: optionalNumber(form.min_payment_amount),
      max_discount_amount: optionalNumber(form.max_discount_amount),
      monthly_discount_limit: optionalNumber(form.monthly_discount_limit),
      monthly_remaining_discount: optionalNumber(form.monthly_remaining_discount)
    });
    resetManualForm();
    success.value = true;
    emit("changed");
  } catch (err) {
    error.value = err.payload || { message: err.message };
  } finally {
    loading.value = false;
  }
}

async function searchCatalog() {
  catalogLoading.value = true;
  catalogError.value = null;
  catalogSuccess.value = "";
  try {
    const payload = await searchCardCatalog({ query: catalogQuery.value });
    catalogCards.value = payload.cards || [];
    catalogSuccess.value = catalogCards.value.length
      ? `${catalogCards.value.length}개의 후보를 찾았습니다.`
      : "검색 결과가 없습니다. 다른 카드명으로 검색해 보세요.";
  } catch (err) {
    catalogError.value = err.payload || { message: err.message };
  } finally {
    catalogLoading.value = false;
  }
}

function selectCatalogCard(card) {
  selectedCatalogCard.value = card;
  Object.assign(catalogDraft, {
    catalog_card_id: card.catalog_card_id,
    card_name: card.card_name,
    issuer_name: card.issuer_name,
    discount_type: card.discount_type,
    discount_value: Number(card.discount_value || 0),
    brand_scope: card.brand_scope || "all",
    min_payment_amount: card.min_payment_amount,
    max_discount_amount: card.max_discount_amount,
    monthly_discount_limit: card.monthly_discount_limit,
    monthly_remaining_discount: card.monthly_remaining_discount,
    user_memo: "카탈로그 후보 확인 후 저장"
  });
  catalogError.value = null;
  catalogSuccess.value = "혜택을 확인한 뒤 저장해 주세요.";
}

function clearCatalogDraft() {
  selectedCatalogCard.value = null;
  Object.assign(catalogDraft, {
    catalog_card_id: null,
    card_name: "",
    issuer_name: "",
    discount_type: "per_liter",
    discount_value: 0,
    brand_scope: "all",
    min_payment_amount: null,
    max_discount_amount: null,
    monthly_discount_limit: null,
    monthly_remaining_discount: null,
    user_memo: ""
  });
  catalogSuccess.value = "";
}

async function saveDraftFromCatalog() {
  const validationMessage = validateDiscountPayload(catalogDraft);
  if (validationMessage) {
    catalogError.value = { message: validationMessage };
    return;
  }

  catalogSaving.value = true;
  catalogError.value = null;
  success.value = false;
  try {
    await createMyCardFromCatalog({
      catalog_card_id: catalogDraft.catalog_card_id,
      discount_type: catalogDraft.discount_type,
      discount_value: Number(catalogDraft.discount_value || 0),
      brand_scope: catalogDraft.brand_scope,
      min_payment_amount: optionalNumber(catalogDraft.min_payment_amount),
      max_discount_amount: optionalNumber(catalogDraft.max_discount_amount),
      monthly_discount_limit: optionalNumber(catalogDraft.monthly_discount_limit),
      monthly_remaining_discount: optionalNumber(catalogDraft.monthly_remaining_discount),
      user_memo: catalogDraft.user_memo
    });
    clearCatalogDraft();
    success.value = true;
    catalogSuccess.value = "카탈로그 후보를 내 카드로 저장했습니다.";
    emit("changed");
  } catch (err) {
    catalogError.value = err.payload || { message: err.message };
  } finally {
    catalogSaving.value = false;
  }
}

async function remove(card) {
  if (!window.confirm(`${card.issuer_name} ${card.card_name} 카드를 삭제할까요?`)) return;

  deletingId.value = card.card_id;
  error.value = null;
  success.value = false;
  try {
    await deleteMyCard(card.card_id);
    success.value = true;
    emit("changed");
  } catch (err) {
    error.value = err.payload || { message: err.message };
  } finally {
    deletingId.value = null;
  }
}

function startEditCard(card) {
  editingCardId.value = card.card_id;
  editCardError.value = null;
  Object.assign(editCardForm, {
    card_name: card.card_name || "",
    issuer_name: card.issuer_name || "",
    discount_type: card.discount_type || "per_liter",
    discount_value: Number(card.discount_value || 0),
    brand_scope: card.brand_scope || "all",
    min_payment_amount: card.min_payment_amount,
    max_discount_amount: card.max_discount_amount,
    monthly_discount_limit: card.monthly_discount_limit,
    monthly_remaining_discount: card.monthly_remaining_discount,
    user_memo: card.user_memo || ""
  });
}

function cancelEditCard() {
  editingCardId.value = null;
  editCardError.value = null;
}

async function saveCardEdit(cardId) {
  if (!editCardForm.issuer_name.trim() || !editCardForm.card_name.trim()) {
    editCardError.value = { message: "카드사와 카드명을 모두 입력해 주세요." };
    return;
  }
  const validationMessage = validateDiscountPayload(editCardForm);
  if (validationMessage) {
    editCardError.value = { message: validationMessage };
    return;
  }

  editCardLoading.value = true;
  editCardError.value = null;
  success.value = false;
  try {
    await updateMyCard(cardId, {
      ...editCardForm,
      discount_value: Number(editCardForm.discount_value || 0),
      min_payment_amount: optionalNumber(editCardForm.min_payment_amount),
      max_discount_amount: optionalNumber(editCardForm.max_discount_amount),
      monthly_discount_limit: optionalNumber(editCardForm.monthly_discount_limit),
      monthly_remaining_discount: optionalNumber(editCardForm.monthly_remaining_discount)
    });
    editingCardId.value = null;
    success.value = true;
    emit("changed");
  } catch (err) {
    editCardError.value = err.payload || { message: err.message };
  } finally {
    editCardLoading.value = false;
  }
}

function imageFailed(url) {
  if (!url) return true;
  return failedImages.value.has(url);
}

function markImageFailed(url) {
  if (!url) return;
  failedImages.value = new Set([...failedImages.value, url]);
}
</script>

<template>
  <main class="workspace">
    <aside class="controls">
      <section class="panel">
        <div class="panelHeader">
          <div>
            <p class="eyebrow">Catalog</p>
            <h2>카드 찾기</h2>
          </div>
        </div>
        <form class="fieldGrid" @submit.prevent="searchCatalog">
          <label>
            <span>카드명 검색</span>
            <input v-model.trim="catalogQuery" placeholder="예: 굿데이, Deep Oil" />
          </label>
          <button class="primaryButton fullWidth" type="submit" :disabled="catalogLoading">
            <Search :size="18" />
            <span>{{ catalogLoading ? "검색 중" : "검색" }}</span>
          </button>
          <div v-if="catalogError" class="errorPanel compact">
            <strong>{{ catalogError.code || "CATALOG_FAILED" }}</strong>
            <span>{{ catalogError.message }}</span>
          </div>
          <p v-if="catalogSuccess" class="successText">{{ catalogSuccess }}</p>
        </form>
      </section>

      <section v-if="selectedCatalogCard" class="panel">
        <div class="panelHeader">
          <div>
            <p class="eyebrow">Confirm</p>
            <h2>혜택 확인</h2>
          </div>
          <button class="iconButton" type="button" title="닫기" @click="clearCatalogDraft">
            <X :size="18" />
          </button>
        </div>
        <div class="cardPreview">
          <div class="cardPreviewIcon">
            <img
              v-if="selectedCatalogCard.card_image_url && !imageFailed(selectedCatalogCard.card_image_url)"
              :src="selectedCatalogCard.card_image_url"
              :alt="catalogDraft.card_name"
              @error="markImageFailed(selectedCatalogCard.card_image_url)"
            />
            <CreditCard v-else :size="22" />
          </div>
          <div>
            <strong>{{ catalogDraft.issuer_name }} {{ catalogDraft.card_name }}</strong>
            <span>{{ selectedCatalogCard.raw_summary || selectedCatalogCard.source_title }}</span>
          </div>
        </div>
        <form class="fieldGrid" @submit.prevent="saveDraftFromCatalog">
          <div class="fieldGrid two">
            <label>
              <span>할인 방식</span>
              <select v-model="catalogDraft.discount_type">
                <option value="per_liter">리터당 할인</option>
                <option value="percentage">결제 금액 비율</option>
                <option value="fixed_amount">정액 할인</option>
              </select>
            </label>
            <label>
              <span>할인값({{ discountUnit(catalogDraft.discount_type) }})</span>
              <input
                v-model.number="catalogDraft.discount_value"
                type="number"
                min="0"
                :max="draftDiscountMax"
                step="0.1"
                required
              />
            </label>
          </div>
          <label>
            <span>적용 주유소</span>
            <select v-model="catalogDraft.brand_scope">
              <option value="all">전체</option>
              <option value="SK">SK</option>
              <option value="GS">GS</option>
              <option value="S_OIL">S-OIL</option>
              <option value="HD_HYUNDAI">HD현대오일뱅크</option>
            </select>
          </label>
          <div class="fieldGrid two">
            <label>
              <span>최대 할인액</span>
              <input v-model.number="catalogDraft.max_discount_amount" type="number" min="0" step="1000" />
            </label>
            <label>
              <span>월 할인 한도</span>
              <input v-model.number="catalogDraft.monthly_discount_limit" type="number" min="0" step="1000" />
            </label>
          </div>
          <label>
            <span>이번 달 남은 할인액</span>
            <input v-model.number="catalogDraft.monthly_remaining_discount" type="number" min="0" step="1000" />
          </label>
          <label>
            <span>메모</span>
            <input v-model.trim="catalogDraft.user_memo" />
          </label>
          <div v-if="catalogError" class="errorPanel compact">
            <strong>{{ catalogError.code || "CATALOG_FAILED" }}</strong>
            <span>{{ catalogError.message }}</span>
          </div>
          <button class="primaryButton fullWidth" type="submit" :disabled="catalogSaving">
            <Check :size="18" />
            <span>{{ catalogSaving ? "저장 중" : "확인 후 저장" }}</span>
          </button>
        </form>
      </section>

      <section class="panel">
        <div class="panelHeader">
          <div>
            <p class="eyebrow">Manual</p>
            <h2>직접 등록</h2>
          </div>
        </div>
        <form class="fieldGrid" @submit.prevent="submit">
          <div class="fieldGrid two">
            <label>
              <span>카드사</span>
              <input v-model.trim="form.issuer_name" required autocomplete="organization" />
            </label>
            <label>
              <span>카드명</span>
              <input v-model.trim="form.card_name" required />
            </label>
          </div>
          <div class="fieldGrid two">
            <label>
              <span>할인 방식</span>
              <select v-model="form.discount_type">
                <option value="per_liter">리터당 할인</option>
                <option value="percentage">결제 금액 비율</option>
                <option value="fixed_amount">정액 할인</option>
              </select>
            </label>
            <label>
              <span>할인값({{ discountUnit(form.discount_type) }})</span>
              <input v-model.number="form.discount_value" type="number" min="0" :max="discountMax" step="1" required />
            </label>
          </div>
          <label>
            <span>적용 주유소</span>
            <select v-model="form.brand_scope">
              <option value="all">전체</option>
              <option value="SK">SK</option>
              <option value="GS">GS</option>
              <option value="S_OIL">S-OIL</option>
              <option value="HD_HYUNDAI">HD현대오일뱅크</option>
            </select>
          </label>
          <div class="fieldGrid two">
            <label>
              <span>최소 결제액</span>
              <input v-model.number="form.min_payment_amount" type="number" min="0" step="1000" />
            </label>
            <label>
              <span>최대 할인액</span>
              <input v-model.number="form.max_discount_amount" type="number" min="0" step="1000" />
            </label>
          </div>
          <label>
            <span>이번 달 남은 할인액</span>
            <input v-model.number="form.monthly_remaining_discount" type="number" min="0" step="1000" />
          </label>
          <div v-if="error" class="errorPanel compact">
            <strong>{{ error.code || "CARD_FAILED" }}</strong>
            <span>{{ error.message }}</span>
          </div>
          <p v-if="success" class="successText">카드가 저장되었습니다.</p>
          <button class="primaryButton fullWidth" type="submit" :disabled="loading">
            <Plus :size="18" />
            <span>{{ loading ? "등록 중" : "등록" }}</span>
          </button>
        </form>
      </section>
    </aside>

    <section class="results">
      <section class="panel">
        <div class="panelHeader">
          <div>
            <p class="eyebrow">Candidates</p>
            <h2>검색 후보 {{ catalogCards.length }}개</h2>
          </div>
        </div>
        <div class="cardList">
          <article v-for="card in catalogCards" :key="card.catalog_card_id" class="cardListItem catalogItem">
            <div class="cardPreviewIcon">
              <img
                v-if="card.card_image_url && !imageFailed(card.card_image_url)"
                :src="card.card_image_url"
                :alt="card.card_name"
                @error="markImageFailed(card.card_image_url)"
              />
              <CreditCard v-else :size="22" />
            </div>
            <div>
              <strong>{{ card.issuer_name }} {{ card.card_name }}</strong>
              <span>{{ card.discount_type }} · {{ card.discount_value }} · {{ card.verification_status }}</span>
            </div>
            <button class="iconButton" type="button" title="혜택 확인" @click="selectCatalogCard(card)">
              <Check :size="18" />
            </button>
          </article>
          <p v-if="catalogCards.length === 0" class="summaryText">검색한 카드 후보가 여기에 표시됩니다.</p>
        </div>
      </section>

      <section class="panel">
        <div class="panelHeader">
          <div>
            <p class="eyebrow">Active</p>
            <h2>내 카드 {{ cards.length }}개</h2>
          </div>
        </div>
        <div class="cardList">
          <article v-for="card in cards" :key="card.card_id" class="cardListItem">
            <div class="cardPreviewIcon">
              <img
                v-if="card.card_image_url && !imageFailed(card.card_image_url)"
                :src="card.card_image_url"
                :alt="card.card_name"
                @error="markImageFailed(card.card_image_url)"
              />
              <CreditCard v-else :size="22" />
            </div>
            <div>
              <strong>{{ card.issuer_name }} {{ card.card_name }}</strong>
              <span>{{ card.discount_type }} · {{ card.discount_value }} · {{ card.brand_scope }}</span>
            </div>
            <button
              class="iconButton"
              type="button"
              title="카드 수정"
              :disabled="editingCardId === card.card_id"
              @click="startEditCard(card)"
            >
              <Pencil :size="18" />
            </button>
            <button
              class="iconButton danger"
              type="button"
              title="카드 삭제"
              :disabled="deletingId === card.card_id"
              @click="remove(card)"
            >
              <Trash2 :size="18" />
            </button>
            <form v-if="editingCardId === card.card_id" class="cardEditForm" @submit.prevent="saveCardEdit(card.card_id)">
              <div class="fieldGrid two">
                <label>
                  <span>카드사</span>
                  <input v-model.trim="editCardForm.issuer_name" required />
                </label>
                <label>
                  <span>카드명</span>
                  <input v-model.trim="editCardForm.card_name" required />
                </label>
              </div>
              <div class="fieldGrid two">
                <label>
                  <span>할인 방식</span>
                  <select v-model="editCardForm.discount_type">
                    <option value="per_liter">리터당 할인</option>
                    <option value="percentage">결제 금액 비율</option>
                    <option value="fixed_amount">정액 할인</option>
                  </select>
                </label>
                <label>
                  <span>할인값({{ discountUnit(editCardForm.discount_type) }})</span>
                  <input v-model.number="editCardForm.discount_value" type="number" min="0" :max="editDiscountMax" step="0.1" required />
                </label>
              </div>
              <label>
                <span>적용 주유소</span>
                <select v-model="editCardForm.brand_scope">
                  <option value="all">전체</option>
                  <option value="SK">SK</option>
                  <option value="GS">GS</option>
                  <option value="S_OIL">S-OIL</option>
                  <option value="HD_HYUNDAI">HD현대오일뱅크</option>
                </select>
              </label>
              <div class="fieldGrid two">
                <label>
                  <span>최소 결제액</span>
                  <input v-model.number="editCardForm.min_payment_amount" type="number" min="0" step="1000" />
                </label>
                <label>
                  <span>최대 할인액</span>
                  <input v-model.number="editCardForm.max_discount_amount" type="number" min="0" step="1000" />
                </label>
              </div>
              <div class="fieldGrid two">
                <label>
                  <span>월 할인 한도</span>
                  <input v-model.number="editCardForm.monthly_discount_limit" type="number" min="0" step="1000" />
                </label>
                <label>
                  <span>이번 달 남은 할인액</span>
                  <input v-model.number="editCardForm.monthly_remaining_discount" type="number" min="0" step="1000" />
                </label>
              </div>
              <label>
                <span>메모</span>
                <input v-model.trim="editCardForm.user_memo" />
              </label>
              <div v-if="editCardError" class="errorPanel compact">
                <strong>{{ editCardError.code || "CARD_UPDATE_FAILED" }}</strong>
                <span>{{ editCardError.message }}</span>
              </div>
              <div class="editActions">
                <button class="primaryButton" type="submit" :disabled="editCardLoading">
                  <Save :size="18" />
                  <span>{{ editCardLoading ? "저장 중" : "수정 저장" }}</span>
                </button>
                <button class="secondaryButton" type="button" :disabled="editCardLoading" @click="cancelEditCard">
                  <X :size="18" />
                  <span>취소</span>
                </button>
              </div>
            </form>
          </article>
          <p v-if="cards.length === 0" class="summaryText">등록된 카드가 없습니다.</p>
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.cardEditForm {
  border-top: 1px solid var(--slate-200);
  display: grid;
  gap: 12px;
  grid-column: 1 / -1;
  margin-top: 12px;
  padding-top: 12px;
}

.editActions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
