import { computed, ref, watch } from "vue";
import { getMyCards } from "../api/cards.js";
import { cardWithEffectiveBenefit } from "../components/cards/cardPresentation.js";

export const NO_DISCOUNT_CARD_ID = "none";

function optionalNumber(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  return Number(value);
}

export function useSavedCards({ isAuthenticated, tempCard }) {
  const cards = ref([]);
  const selectedCardId = ref(NO_DISCOUNT_CARD_ID);
  const selectedSavedCard = computed(() => {
    return cards.value.find((card) => String(card.card_id) === String(selectedCardId.value)) || null;
  });

  async function loadCards() {
    const payload = await getMyCards();
    cards.value = payload.cards || [];
  }

  function clearCards() {
    cards.value = [];
  }

  watch(
    cards,
    (nextCards) => {
      if (!isAuthenticated?.value) {
        selectedCardId.value = NO_DISCOUNT_CARD_ID;
        return;
      }

      if (!nextCards.length) {
        selectedCardId.value = NO_DISCOUNT_CARD_ID;
        return;
      }

      const stillAvailable = nextCards.some(
        (card) => String(card.card_id) === String(selectedCardId.value)
      );
      if (!stillAvailable) {
        selectedCardId.value = nextCards[0].card_id;
      }
    },
    { immediate: true }
  );

  function cardToRecommendationPayload(sourceCard) {
    const card = cardWithEffectiveBenefit(sourceCard);
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
      source_type: card.source_type,
      verification_status: card.verification_status,
      card_image_url: card.card_image_url,
      source_url: card.source_url,
    };
  }

  function selectedCards() {
    if (isAuthenticated?.value) {
      return selectedSavedCard.value ? [cardToRecommendationPayload(selectedSavedCard.value)] : [];
    }

    if (!tempCard.enabled) {
      return [];
    }

    return [
      cardToRecommendationPayload(tempCard),
    ];
  }

  return {
    cards,
    selectedCardId,
    selectedSavedCard,
    loadCards,
    clearCards,
    selectedCards,
  };
}
