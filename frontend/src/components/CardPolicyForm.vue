<script setup>
import { ChevronDown, CreditCard, Sparkles } from "@lucide/vue";
import { ref, watch } from "vue";

const props = defineProps({
  cards: {
    type: Array,
    default: () => []
  }
});

const model = defineModel({ required: true });

// Popular real-world card presets to decrease input friction
const cardPresets = [
  {
    name: "신한 Deep Oil",
    issuer: "신한카드",
    type: "percentage",
    value: 10,
    brand: "all",
    minPay: 20000,
    maxLimit: 15000,
    remaining: 15000,
    previousMonthSpending: 300000
  },
  {
    name: "삼성 iD Auto",
    issuer: "삼성카드",
    type: "per_liter",
    value: 100,
    brand: "all",
    minPay: 30000,
    maxLimit: 20000,
    remaining: 20000,
    previousMonthSpending: 300000
  },
  {
    name: "S-OIL 신한 MyCar",
    issuer: "신한카드",
    type: "per_liter",
    value: 120,
    brand: "S_OIL",
    minPay: null,
    maxLimit: 15000,
    remaining: 12000,
    previousMonthSpending: null
  },
  {
    name: "현대카드 M3 Edition3",
    issuer: "현대카드",
    type: "per_liter",
    value: 150,
    brand: "GS",
    minPay: 50000,
    maxLimit: 30000,
    remaining: 30000,
    previousMonthSpending: 500000
  }
];

function applyPreset(preset) {
  model.value.enabled = true;
  model.value.issuer_name = preset.issuer;
  model.value.card_name = preset.name;
  model.value.discount_type = preset.type;
  model.value.discount_value = preset.value;
  model.value.brand_scope = preset.brand;
  model.value.min_payment_amount = preset.minPay;
  model.value.max_discount_amount = preset.maxLimit;
  model.value.monthly_remaining_discount = preset.remaining;
  model.value.previous_month_spending = preset.previousMonthSpending;
}

function applyMyCard(cardId) {
  if (!cardId) return;
  const card = props.cards.find(c => String(c.card_id) === String(cardId));
  if (!card) return;

  model.value.enabled = true;
  model.value.issuer_name = card.issuer_name;
  model.value.card_name = card.card_name;
  model.value.discount_type = card.discount_type;
  model.value.discount_value = card.discount_value;
  model.value.brand_scope = card.brand_scope;
  model.value.min_payment_amount = card.min_payment_amount;
  model.value.max_discount_amount = card.max_discount_amount;
  model.value.monthly_remaining_discount = card.monthly_remaining_discount;
  model.value.previous_month_spending = card.previous_month_spending;
}
</script>

<template>
  <section class="panel">
    <div class="panelHeader" style="margin-bottom: 12px; border-bottom: 0; padding-bottom: 0;">
      <div>
        <p class="eyebrow">Card Discount</p>
        <h2>임의 카드 할인 시뮬레이션</h2>
      </div>
      <label class="switchControl">
        <input v-model="model.enabled" type="checkbox" />
        <span>{{ model.enabled ? "활성" : "비활성" }}</span>
      </label>
    </div>

    <!-- 내 등록 카드 시뮬레이션 대입 드롭다운 -->
    <div v-if="cards && cards.length > 0" style="margin-bottom: 16px;">
      <span style="font-size: 11px; font-weight: 800; color: var(--slate-400); text-transform: uppercase; display: flex; align-items: center; gap: 4px; margin-bottom: 8px;">
        💳 내 등록 카드 빠른 선택 (시뮬레이션 반영)
      </span>
      <select @change="applyMyCard($event.target.value)" style="width: 100%; border: 1px solid var(--slate-200); border-radius: var(--radius-sm); padding: 10px 12px; font-size: 13px; font-weight: 700; color: var(--slate-700); background-color: var(--slate-50); outline: none; transition: border-color 0.2s;">
        <option value="">-- 내 카드 중에서 선택하여 테스트 --</option>
        <option
          v-for="card in cards"
          :key="card.card_id"
          :value="card.card_id"
        >
          [{{ card.issuer_name }}] {{ card.card_name }} ({{ card.discount_type === 'per_liter' ? 'L당 ' + card.discount_value + '원' : card.discount_type === 'percentage' ? card.discount_value + '%' : card.discount_value + '원' }} 할인)
        </option>
      </select>
    </div>

    <!-- Smart Card Presets Tag Cloud -->
    <div style="margin-bottom: 16px;">
      <span style="font-size: 11px; font-weight: 800; color: var(--slate-400); text-transform: uppercase; display: flex; align-items: center; gap: 4px; margin-bottom: 8px;">
        <Sparkles :size="10" /> 인기 주유 카드 빠른 적용
      </span>
      <div class="cardPresets">
        <button
          v-for="preset in cardPresets"
          :key="preset.name"
          class="presetTag"
          type="button"
          @click="applyPreset(preset)"
        >
          {{ preset.name }}
        </button>
      </div>
    </div>

    <!-- Preview Widget -->
    <div class="cardPreview" :style="{ borderLeft: model.enabled ? '4px solid var(--primary)' : '1px solid var(--slate-200)' }">
      <div class="cardPreviewIcon" :style="{ background: model.enabled ? 'var(--primary-light)' : 'var(--slate-100)', color: model.enabled ? 'var(--primary)' : 'var(--slate-400)' }">
        <CreditCard :size="24" />
      </div>
      <div>
        <strong>{{ model.issuer_name || "카드사 미정" }} {{ model.card_name || "카드 혜택 없음" }}</strong>
        <span :style="{ color: model.enabled ? 'var(--primary)' : 'var(--slate-400)', fontWeight: 700 }">
          {{ model.enabled ? `${model.discount_type === 'per_liter' ? 'L당 ' + model.discount_value + '원' : model.discount_type === 'percentage' ? model.discount_value + '%' : model.discount_value + '원'} 할인 반영` : "미적용 상태" }}
        </span>
      </div>
    </div>

    <!-- Collapsible detailed fields (Clears clutter when disabled) -->
    <div v-if="model.enabled" class="fieldGrid" style="border-top: 1px dashed var(--slate-200); padding-top: 16px;">
      <div class="fieldGrid two">
        <label>
          <span>카드사</span>
          <input v-model.trim="model.issuer_name" placeholder="예: 신한카드" />
        </label>
        <label>
          <span>카드명</span>
          <input v-model.trim="model.card_name" placeholder="예: Deep Oil" />
        </label>
      </div>

      <div class="fieldGrid two">
        <label>
          <span>할인 방식</span>
          <select v-model="model.discount_type">
            <option value="per_liter">리터당 할인 (원)</option>
            <option value="percentage">결제액 비율 (%)</option>
            <option value="fixed_amount">정액 할인 (원)</option>
          </select>
        </label>
        <label>
          <span>할인값</span>
          <input v-model.number="model.discount_value" type="number" min="0" step="1" />
        </label>
      </div>

      <label>
        <span>혜택 브랜드 범위</span>
        <select v-model="model.brand_scope">
          <option value="all">모든 주유소 브랜드 공통</option>
          <option value="SK">SK에너지 전용</option>
          <option value="GS">GS칼텍스 전용</option>
          <option value="S_OIL">S-OIL 전용</option>
          <option value="HD_HYUNDAI">HD현대오일뱅크 전용</option>
        </select>
      </label>

      <div class="fieldGrid two">
        <label>
          <span>최소 결제액 (원)</span>
          <input v-model.number="model.min_payment_amount" type="number" min="0" step="1000" placeholder="제한 없음" />
        </label>
        <label>
          <span>최대 할인한도 (원)</span>
          <input v-model.number="model.max_discount_amount" type="number" min="0" step="1000" placeholder="제한 없음" />
        </label>
      </div>

      <label>
        <span>이번 달 남은 한도 (원)</span>
        <input v-model.number="model.monthly_remaining_discount" type="number" min="0" step="1000" placeholder="한도 무제한" />
      </label>

      <label>
        <span>전월 실적 (원)</span>
        <input v-model.number="model.previous_month_spending" type="number" min="0" step="10000" placeholder="조건 없음" />
      </label>
    </div>
  </section>
</template>

