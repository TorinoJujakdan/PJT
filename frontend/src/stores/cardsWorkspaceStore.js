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

export function resetCardsWorkspace() {
  Object.assign(cardsWorkspaceStore, createInitialState());
}

export function markCardsWorkspaceDirty(area) {
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
