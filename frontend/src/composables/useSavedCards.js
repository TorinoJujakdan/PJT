import { ref } from "vue";
import { getMyCards } from "../api/cards";
import { cardWithEffectiveBenefit } from "../components/cards/cardPresentation";

function optionalNumber(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  return Number(value);
}

export function useSavedCards({ isAuthenticated, tempCard }) {
  const cards = ref([]);

  async function loadCards() {
    const payload = await getMyCards();
    cards.value = payload.cards || [];
  }

  function clearCards() {
    cards.value = [];
  }

  function selectedCards() {
    if (isAuthenticated?.value) {
      return cards.value.map((c) => {
        const card = cardWithEffectiveBenefit(c);
        return {
          card_id: card.card_id,
          card_name: card.card_name,
          issuer_name: card.issuer_name,
          discount_type: card.discount_type,
          discount_value: Number(card.discount_value || 0),
          brand_scope: card.brand_scope || "all",
          min_payment_amount: optionalNumber(card.min_payment_amount),
          max_discount_amount: optionalNumber(card.max_discount_amount),
          monthly_remaining_discount: optionalNumber(card.monthly_remaining_discount),
          previous_month_spending: optionalNumber(card.previous_month_spending),
        };
      });
    }

    if (!tempCard.enabled) {
      return [];
    }

    return [
      {
        card_id: tempCard.card_id,
        card_name: tempCard.card_name,
        issuer_name: tempCard.issuer_name,
        discount_type: tempCard.discount_type,
        discount_value: Number(tempCard.discount_value || 0),
        brand_scope: tempCard.brand_scope || "all",
        min_payment_amount: optionalNumber(tempCard.min_payment_amount),
        max_discount_amount: optionalNumber(tempCard.max_discount_amount),
        monthly_remaining_discount: optionalNumber(tempCard.monthly_remaining_discount),
        previous_month_spending: optionalNumber(tempCard.previous_month_spending),
      },
    ];
  }

  return {
    cards,
    loadCards,
    clearCards,
    selectedCards,
  };
}
