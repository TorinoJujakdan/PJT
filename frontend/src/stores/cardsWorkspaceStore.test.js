import assert from "node:assert/strict";
import test from "node:test";

import {
  blankCardDraft,
  cardsWorkspaceStore,
  createCardDraftCopy,
  markCardsWorkspaceClean,
  markCardsWorkspaceDirty,
  replaceCardDraft,
  resetCardsWorkspace,
} from "./cardsWorkspaceStore.js";

test("keeps card workspace values while the view stays mounted", () => {
  resetCardsWorkspace();

  cardsWorkspaceStore.activeTab = "manual";
  cardsWorkspaceStore.catalogQuery = "KB";
  cardsWorkspaceStore.manualDraft.card_name = "KB Oil Card";
  markCardsWorkspaceDirty("manual");

  assert.equal(cardsWorkspaceStore.activeTab, "manual");
  assert.equal(cardsWorkspaceStore.catalogQuery, "KB");
  assert.equal(cardsWorkspaceStore.manualDraft.card_name, "KB Oil Card");
  assert.equal(cardsWorkspaceStore.isDirty, true);
});

test("reset restores the card workspace defaults", () => {
  cardsWorkspaceStore.activeTab = "saved";
  cardsWorkspaceStore.catalogQuery = "test";
  cardsWorkspaceStore.manualDraft.card_name = "Test Card";

  resetCardsWorkspace();

  assert.equal(cardsWorkspaceStore.activeTab, "catalog");
  assert.equal(cardsWorkspaceStore.catalogQuery, "");
  assert.equal(cardsWorkspaceStore.manualDraft.card_name, "");
  assert.equal(cardsWorkspaceStore.isDirty, false);
});

test("cleaning dirty state does not erase in-progress draft values", () => {
  resetCardsWorkspace();
  cardsWorkspaceStore.manualDraft.card_name = "Shinhan Oil Card";
  cardsWorkspaceStore.dirtyAreas.manual = true;
  cardsWorkspaceStore.isDirty = true;

  markCardsWorkspaceClean();

  assert.equal(cardsWorkspaceStore.manualDraft.card_name, "Shinhan Oil Card");
  assert.equal(cardsWorkspaceStore.isDirty, false);
});

test("cleaning one area preserves another dirty area", () => {
  resetCardsWorkspace();
  markCardsWorkspaceDirty("manual");
  markCardsWorkspaceDirty("catalog");

  markCardsWorkspaceClean("catalog");

  assert.equal(cardsWorkspaceStore.dirtyAreas.catalog, false);
  assert.equal(cardsWorkspaceStore.dirtyAreas.manual, true);
  assert.equal(cardsWorkspaceStore.isDirty, true);
});

test("local card draft copies are isolated from their source while typing", () => {
  const source = { card_name: "Source Card", discount_value: 120 };
  const draft = createCardDraftCopy(source);

  draft.card_name = "Local Input";

  assert.equal(source.card_name, "Source Card");
  assert.equal(draft.discount_type, blankCardDraft.discount_type);
  assert.equal(draft.card_name, "Local Input");
});

test("replacing a draft preserves defaults while applying submitted values", () => {
  const target = createCardDraftCopy({ card_name: "Before", issuer_name: "A" });

  replaceCardDraft(target, {
    card_name: "After",
    issuer_name: "B",
    discount_value: 150,
    previous_month_spending: 300000,
  });

  assert.equal(target.card_name, "After");
  assert.equal(target.issuer_name, "B");
  assert.equal(target.discount_value, 150);
  assert.equal(target.previous_month_spending, 300000);
  assert.equal(target.brand_scope, blankCardDraft.brand_scope);
});


test("card draft defaults include previous month spending", () => {
  const draft = createCardDraftCopy({ card_name: "실적 카드" });

  assert.equal(blankCardDraft.previous_month_spending, null);
  assert.equal(draft.previous_month_spending, null);
});
