import { reactive } from "vue";

export const blankCardDraft = Object.freeze({
  card_name: "",
  issuer_name: "",
  discount_type: "per_liter",
  discount_value: 80,
  brand_scope: "all",
  min_payment_amount: null,
  max_discount_amount: null,
  monthly_discount_limit: null,
  monthly_remaining_discount: null,
  previous_month_spending: null,
  user_memo: "",
});

function createInitialState() {
  return {
    activeTab: "catalog",
    catalogQuery: "",
    catalogCards: [],
    selectedCatalogCard: null,
    catalogDraft: { ...blankCardDraft, catalog_card_id: null },
    manualDraft: { ...blankCardDraft },
    editingCardId: null,
    editDraft: { ...blankCardDraft },
    deleteTarget: null,
    dirtyAreas: { catalog: false, manual: false, edit: false },
    isDirty: false,
  };
}

export const cardsWorkspaceStore = reactive(createInitialState());

// Form panels own hot local typing state for responsiveness. These store drafts
// are persistence snapshots used when a panel is submitted, unmounted, or reopened.
export function createCardDraftCopy(source) {
  return { ...blankCardDraft, ...source };
}

export function replaceCardDraft(target, source) {
  Object.assign(target, createCardDraftCopy(source));
}

export function resetCardsWorkspace() {
  Object.assign(cardsWorkspaceStore, createInitialState());
}

export function markCardsWorkspaceDirty(area) {
  if (cardsWorkspaceStore.dirtyAreas[area]) return;
  cardsWorkspaceStore.dirtyAreas[area] = true;
  cardsWorkspaceStore.isDirty = true;
}

export function markCardsWorkspaceClean(area) {
  if (area) {
    cardsWorkspaceStore.dirtyAreas[area] = false;
  } else {
    Object.keys(cardsWorkspaceStore.dirtyAreas).forEach((key) => {
      cardsWorkspaceStore.dirtyAreas[key] = false;
    });
  }
  cardsWorkspaceStore.isDirty = Object.values(cardsWorkspaceStore.dirtyAreas).some(Boolean);
}
