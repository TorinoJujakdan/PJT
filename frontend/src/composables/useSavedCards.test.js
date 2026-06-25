import assert from "node:assert/strict";
import test from "node:test";

import { nextTick, reactive, ref } from "vue";

import { NO_DISCOUNT_CARD_ID, useSavedCards } from "./useSavedCards.js";

function card(overrides = {}) {
  return {
    card_id: overrides.card_id ?? 1,
    card_name: overrides.card_name ?? "Fuel Saver",
    issuer_name: overrides.issuer_name ?? "Smart Bank",
    discount_type: overrides.discount_type ?? "per_liter",
    discount_value: overrides.discount_value ?? 80,
    brand_scope: overrides.brand_scope ?? "all",
    min_payment_amount: null,
    max_discount_amount: null,
    monthly_remaining_discount: null,
    previous_month_spending: null,
    source_type: "manual",
    verification_status: "user_confirmed",
    card_image_url: null,
    source_url: null,
  };
}

test("defaults to the first saved card and sends only that card", async () => {
  const saved = useSavedCards({
    isAuthenticated: ref(true),
    tempCard: reactive({ enabled: false }),
  });

  saved.cards.value = [
    card({ card_id: 10, card_name: "First Card" }),
    card({ card_id: 20, card_name: "Second Card" }),
  ];
  await nextTick();

  assert.equal(saved.selectedCardId.value, 10);
  assert.deepEqual(
    saved.selectedCards().map((item) => item.card_id),
    [10]
  );
});

test("uses the selected saved card instead of every saved card", async () => {
  const saved = useSavedCards({
    isAuthenticated: ref(true),
    tempCard: reactive({ enabled: false }),
  });

  saved.cards.value = [
    card({ card_id: 10, card_name: "First Card" }),
    card({ card_id: 20, card_name: "Second Card" }),
  ];
  saved.selectedCardId.value = 20;
  await nextTick();

  const payload = saved.selectedCards();
  assert.equal(payload.length, 1);
  assert.equal(payload[0].card_id, 20);
  assert.equal(payload[0].card_name, "Second Card");
});

test("can explicitly disable card benefits for authenticated quotes", async () => {
  const saved = useSavedCards({
    isAuthenticated: ref(true),
    tempCard: reactive({ enabled: false }),
  });

  saved.cards.value = [card({ card_id: 10 })];
  await nextTick();
  saved.selectedCardId.value = NO_DISCOUNT_CARD_ID;

  assert.deepEqual(saved.selectedCards(), []);
});
