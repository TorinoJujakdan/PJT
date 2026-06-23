const brandLabels = {
  all: "모든 주유소",
  SK: "SK에너지",
  GS: "GS칼텍스",
  S_OIL: "S-OIL",
  HD_HYUNDAI: "HD현대오일뱅크",
};

export function discountLabel(card) {
  const benefit = cardWithEffectiveBenefit(card);
  const value = Number(benefit?.discount_value || 0).toLocaleString("ko-KR");
  if (benefit?.discount_type === "percentage") return `결제 금액의 ${value}% 할인`;
  if (benefit?.discount_type === "fixed_amount") return `건당 ${value}원 할인`;
  return `리터당 ${value}원 할인`;
}

export function brandLabel(scope) {
  return brandLabels[scope] || scope || "모든 주유소";
}

export function wonLabel(value) {
  if (value === null || value === undefined || value === "") return "제한 정보 없음";
  return `${Number(value).toLocaleString("ko-KR")}원`;
}

export function trustDisclosure(card) {
  if (!card?.source_url) {
    return {
      tone: "caution",
      title: "출처 링크가 없는 참고 정보예요",
      description: "등록 전 카드사 상품 안내에서 최신 주유 혜택과 이용 조건을 꼭 확인해 주세요.",
    };
  }
  if (card.verification_status === "admin_verified") {
    return {
      tone: "verified",
      title: "출처가 확인된 혜택 정보예요",
      description: "그래도 카드사 정책 변경에 따라 실제 혜택이 달라질 수 있어요.",
    };
  }
  return {
    tone: "caution",
    title: "수집된 정보를 사용자가 확인하고 등록해요",
    description: "아래 출처에서 최신 혜택과 전월 실적 조건을 확인한 뒤 등록해 주세요.",
  };
}

export function validateCardDraft(draft) {
  if (!draft.issuer_name?.trim() || !draft.card_name?.trim()) {
    return "카드사와 카드명을 모두 입력해 주세요.";
  }
  const value = Number(draft.discount_value);
  if (Number.isNaN(value) || value < 0) return "할인값은 0 이상의 숫자로 입력해 주세요.";
  if (draft.discount_type === "percentage" && value > 100) {
    return "비율 할인은 100%를 초과할 수 없습니다.";
  }
  return "";
}

function firstBenefit(benefits) {
  return Array.isArray(benefits) && benefits.length > 0 ? benefits[0] : null;
}

export function effectiveBenefit(card) {
  return (
    card?.effective_benefit
    || firstBenefit(card?.catalog_benefit_tiers)
    || firstBenefit(card?.benefit_tiers)
    || null
  );
}

export function cardWithEffectiveBenefit(card) {
  const benefit = effectiveBenefit(card);
  if (!benefit) return card || {};

  return {
    ...(card || {}),
    discount_type: benefit.discount_type || card?.discount_type || "per_liter",
    discount_value: benefit.discount_value ?? card?.discount_value ?? 0,
    brand_scope: benefit.brand_scope || card?.brand_scope || "all",
    min_payment_amount: benefit.min_payment_amount ?? card?.min_payment_amount ?? null,
    monthly_discount_limit: benefit.monthly_discount_limit ?? card?.monthly_discount_limit ?? null,
  };
}

export function cardPayload(draft) {
  const optionalNumber = (value) => (
    value === "" || value === null || value === undefined ? null : Number(value)
  );
  const benefitDraft = cardWithEffectiveBenefit(draft);
  return {
    card_name: benefitDraft.card_name,
    issuer_name: benefitDraft.issuer_name,
    discount_type: benefitDraft.discount_type,
    discount_value: Number(benefitDraft.discount_value || 0),
    brand_scope: benefitDraft.brand_scope || "all",
    min_payment_amount: optionalNumber(benefitDraft.min_payment_amount),
    max_discount_amount: optionalNumber(benefitDraft.max_discount_amount),
    monthly_discount_limit: optionalNumber(benefitDraft.monthly_discount_limit),
    monthly_remaining_discount: optionalNumber(benefitDraft.monthly_remaining_discount),
    previous_month_spending: optionalNumber(benefitDraft.previous_month_spending),
    user_memo: benefitDraft.user_memo || "",
  };
}

export function catalogCardDraft(card) {
  return {
    ...cardPayload({
      ...cardWithEffectiveBenefit(card),
      user_memo: "카탈로그 혜택 확인 후 등록",
    }),
    catalog_card_id: card.catalog_card_id,
  };
}

export function catalogCardPayload(draft) {
  const { card_name, issuer_name, ...payload } = cardPayload(draft);
  return { ...payload, catalog_card_id: draft.catalog_card_id };
}
