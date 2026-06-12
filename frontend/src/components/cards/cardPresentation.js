const brandLabels = {
  all: "모든 주유소",
  SK: "SK에너지",
  GS: "GS칼텍스",
  S_OIL: "S-OIL",
  HD_HYUNDAI: "HD현대오일뱅크",
};

export function discountLabel(card) {
  const value = Number(card?.discount_value || 0).toLocaleString("ko-KR");
  if (card?.discount_type === "percentage") return `결제 금액의 ${value}% 할인`;
  if (card?.discount_type === "fixed_amount") return `건당 ${value}원 할인`;
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

export function cardPayload(draft) {
  const optionalNumber = (value) => (
    value === "" || value === null || value === undefined ? null : Number(value)
  );
  return {
    card_name: draft.card_name,
    issuer_name: draft.issuer_name,
    discount_type: draft.discount_type,
    discount_value: Number(draft.discount_value || 0),
    brand_scope: draft.brand_scope,
    min_payment_amount: optionalNumber(draft.min_payment_amount),
    max_discount_amount: optionalNumber(draft.max_discount_amount),
    monthly_discount_limit: optionalNumber(draft.monthly_discount_limit),
    monthly_remaining_discount: optionalNumber(draft.monthly_remaining_discount),
    user_memo: draft.user_memo || "",
  };
}

export function catalogCardPayload(draft) {
  const { card_name, issuer_name, ...payload } = cardPayload(draft);
  return { ...payload, catalog_card_id: draft.catalog_card_id };
}
