import assert from "node:assert/strict";
import test from "node:test";

import {
  cardsWorkspaceStore,
  markCardsWorkspaceClean,
  markCardsWorkspaceDirty,
  resetCardsWorkspace,
} from "./cardsWorkspaceStore.js";

test("카드 작업 상태는 뷰가 다시 열려도 유지된다", () => {
  resetCardsWorkspace();

  cardsWorkspaceStore.activeTab = "manual";
  cardsWorkspaceStore.catalogQuery = "국민";
  cardsWorkspaceStore.manualDraft.card_name = "국민 오일카드";
  markCardsWorkspaceDirty("manual");

  assert.equal(cardsWorkspaceStore.activeTab, "manual");
  assert.equal(cardsWorkspaceStore.catalogQuery, "국민");
  assert.equal(cardsWorkspaceStore.manualDraft.card_name, "국민 오일카드");
  assert.equal(cardsWorkspaceStore.isDirty, true);
});

test("명시적 초기화는 카드 작업 상태를 기본값으로 되돌린다", () => {
  cardsWorkspaceStore.activeTab = "saved";
  cardsWorkspaceStore.catalogQuery = "테스트";
  cardsWorkspaceStore.manualDraft.card_name = "테스트 카드";

  resetCardsWorkspace();

  assert.equal(cardsWorkspaceStore.activeTab, "catalog");
  assert.equal(cardsWorkspaceStore.catalogQuery, "");
  assert.equal(cardsWorkspaceStore.manualDraft.card_name, "");
  assert.equal(cardsWorkspaceStore.isDirty, false);
});

test("저장 완료 표시는 입력값을 지우지 않고 dirty 상태만 해제한다", () => {
  resetCardsWorkspace();
  cardsWorkspaceStore.manualDraft.card_name = "신한 오일카드";
  cardsWorkspaceStore.dirtyAreas.manual = true;
  cardsWorkspaceStore.isDirty = true;

  markCardsWorkspaceClean();

  assert.equal(cardsWorkspaceStore.manualDraft.card_name, "신한 오일카드");
  assert.equal(cardsWorkspaceStore.isDirty, false);
});

test("한 흐름을 저장해도 다른 탭의 작성 중 상태는 유지된다", () => {
  resetCardsWorkspace();
  markCardsWorkspaceDirty("manual");
  markCardsWorkspaceDirty("catalog");

  markCardsWorkspaceClean("catalog");

  assert.equal(cardsWorkspaceStore.dirtyAreas.catalog, false);
  assert.equal(cardsWorkspaceStore.dirtyAreas.manual, true);
  assert.equal(cardsWorkspaceStore.isDirty, true);
});
