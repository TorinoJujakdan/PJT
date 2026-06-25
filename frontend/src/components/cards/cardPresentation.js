const brandLabels = {
  all: "모든 주유소",
  SK: "SK에너지",
  GS: "GS칼텍스",
  S_OIL: "S-OIL",
  HD_HYUNDAI: "HD현대오일뱅크",
};

export function requiresManualBenefitEntry(card) {
  return Boolean(
    card?.requires_manual_benefit_entry
    || (card?.fuel_benefit_status && card.fuel_benefit_status !== "verified"),
  );
}

export function fuelBenefitStatusLabel(card) {
  switch (card?.fuel_benefit_status) {
    case "verified":
      return "검증된 주유 혜택";
    case "held_relevance_missing":
      return "주유 혜택 확인 필요";
    case "skipped_insufficient_source":
      return "출처 정보 부족";
    case "unknown":
      return "재검증 대기";
    default:
      return requiresManualBenefitEntry(card) ? "주유 혜택 확인 필요" : "검증된 주유 혜택";
  }
}

export function manualBenefitNotice(card) {
  switch (card?.fuel_benefit_status) {
    case "held_relevance_missing":
      return "수집된 혜택이 주유 할인과 직접 관련되지 않아 자동 등록할 수 없어요. 카드사에서 실제 주유 조건을 확인한 뒤 아래 값을 입력해 주세요.";
    case "skipped_insufficient_source":
      return "출처나 원문이 부족해 주유 할인 조건을 확정하지 못했어요. 카드사 안내를 확인하고 직접 조건을 입력해 주세요.";
    case "unknown":
      return "아직 새 검증 기준으로 재확인되지 않은 카드예요. 등록하려면 주유 할인 조건을 직접 입력해 주세요.";
    default:
      return requiresManualBenefitEntry(card)
        ? "주유 혜택을 확정하려면 직접 확인한 할인 조건을 입력해 주세요."
        : "검증된 주유 혜택을 기본값으로 등록할 수 있어요.";
  }
}

export function discountLabel(card) {
  if (requiresManualBenefitEntry(card)) return fuelBenefitStatusLabel(card);
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
  if (requiresManualBenefitEntry(draft) && value <= 0) {
    return "확인 필요 카드는 직접 확인한 0보다 큰 주유 할인값을 입력해야 등록할 수 있습니다.";
  }
  if (draft.discount_type === "percentage" && value > 100) {
    return "비율 할인은 100%를 초과할 수 없습니다.";
  }
  return "";
}

function firstBenefit(benefits) {
  return Array.isArray(benefits) && benefits.length > 0 ? benefits[0] : null;
}

export function effectiveBenefit(card) {
  if (requiresManualBenefitEntry(card)) return null;
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
  const needsManualEntry = requiresManualBenefitEntry(card);
  const baseCard = cardWithEffectiveBenefit(card);
  return {
    ...cardPayload({
      ...baseCard,
      discount_type: needsManualEntry ? "per_liter" : baseCard.discount_type,
      discount_value: needsManualEntry ? "" : baseCard.discount_value,
      brand_scope: needsManualEntry ? "all" : baseCard.brand_scope,
      user_memo: needsManualEntry ? "주유 혜택 직접 확인 후 등록" : "카탈로그 혜택 확인 후 등록",
    }),
    fuel_benefit_status: card.fuel_benefit_status || "verified",
    requires_manual_benefit_entry: needsManualEntry,
    catalog_card_id: card.catalog_card_id,
  };
}

export function catalogCardPayload(draft) {
  const { card_name, issuer_name, ...payload } = cardPayload(draft);
  return { ...payload, catalog_card_id: draft.catalog_card_id };
}
