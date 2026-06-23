import assert from "node:assert/strict";
import test from "node:test";

import {
  cardPayload,
  catalogCardPayload,
  discountLabel,
  trustDisclosure,
  validateCardDraft,
} from "./cardPresentation.js";

test("내부 할인 코드를 사용자 친화적인 한국어 혜택으로 변환한다", () => {
  assert.equal(discountLabel({ discount_type: "per_liter", discount_value: 80 }), "리터당 80원 할인");
  assert.equal(discountLabel({ discount_type: "percentage", discount_value: 7 }), "결제 금액의 7% 할인");
});

test("출처 없음과 미검증 출처를 서로 다른 안내로 구분한다", () => {
  const missing = trustDisclosure({ source_url: "", verification_status: "unverified" });
  const collected = trustDisclosure({
    source_url: "https://example.com/card",
    verification_status: "unverified",
  });
  assert.match(missing.title, /출처 링크가 없는/);
  assert.match(collected.title, /사용자가 확인/);
});

test("비율 할인은 100퍼센트를 넘을 수 없다", () => {
  assert.match(validateCardDraft({
    issuer_name: "테스트",
    card_name: "카드",
    discount_type: "percentage",
    discount_value: 120,
  }), /100%/);
});

test("쓰기 payload에는 서버 응답 전용 필드가 포함되지 않는다", () => {
  const draft = {
    card_id: 10,
    source_type: "manual",
    verification_status: "user_confirmed",
    card_name: "카드",
    issuer_name: "카드사",
    discount_type: "per_liter",
    discount_value: 80,
    brand_scope: "all",
  };
  assert.equal("card_id" in cardPayload(draft), false);
  assert.equal("source_type" in cardPayload(draft), false);
  assert.deepEqual(catalogCardPayload({ ...draft, catalog_card_id: 3 }).catalog_card_id, 3);
});

test("쓰기 payload에는 전월 실적 입력값을 숫자 또는 null로 포함한다", () => {
  const draft = {
    card_name: "카드",
    issuer_name: "카드사",
    discount_type: "per_liter",
    discount_value: 80,
    brand_scope: "all",
    previous_month_spending: "300000",
  };

  assert.equal(cardPayload(draft).previous_month_spending, 300000);
  assert.equal(cardPayload({ ...draft, previous_month_spending: "" }).previous_month_spending, null);
  assert.equal(catalogCardPayload({ ...draft, catalog_card_id: 3 }).previous_month_spending, 300000);
});
