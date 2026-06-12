<script setup>
defineProps({
  draft: { type: Object, required: true },
  advanced: { type: Boolean, default: true },
});

defineEmits(["dirty"]);
</script>

<template>
  <div class="cardFormGrid" @input="$emit('dirty')" @change="$emit('dirty')">
    <label>
      <span>할인 방식</span>
      <select v-model="draft.discount_type">
        <option value="per_liter">리터당 할인</option>
        <option value="percentage">결제 금액 비율 할인</option>
        <option value="fixed_amount">건당 정액 할인</option>
      </select>
    </label>
    <label>
      <span>할인값 {{ draft.discount_type === "percentage" ? "(%)" : "(원)" }}</span>
      <input v-model.number="draft.discount_value" type="number" min="0" :max="draft.discount_type === 'percentage' ? 100 : undefined" required />
    </label>
    <label>
      <span>적용 주유소</span>
      <select v-model="draft.brand_scope">
        <option value="all">모든 주유소</option>
        <option value="SK">SK에너지</option>
        <option value="GS">GS칼텍스</option>
        <option value="S_OIL">S-OIL</option>
        <option value="HD_HYUNDAI">HD현대오일뱅크</option>
      </select>
    </label>
    <template v-if="advanced">
      <label>
        <span>최소 결제 금액 <small>(선택, 원)</small></span>
        <input v-model.number="draft.min_payment_amount" type="number" min="0" step="1000" />
      </label>
      <label>
        <span>건당 최대 할인 <small>(선택, 원)</small></span>
        <input v-model.number="draft.max_discount_amount" type="number" min="0" step="1000" />
      </label>
      <label>
        <span>월 할인 한도 <small>(선택, 원)</small></span>
        <input v-model.number="draft.monthly_discount_limit" type="number" min="0" step="1000" />
      </label>
      <label>
        <span>이번 달 남은 한도 <small>(선택, 원)</small></span>
        <input v-model.number="draft.monthly_remaining_discount" type="number" min="0" step="1000" />
      </label>
    </template>
  </div>
</template>
