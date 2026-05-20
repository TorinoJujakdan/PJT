<script setup>
defineProps({
  cost: {
    type: Object,
    required: true
  }
});

function won(value) {
  return `${Number(value).toLocaleString("ko-KR")}원`;
}
</script>

<template>
  <div class="breakdown">
    <div>
      <span>주유비</span>
      <strong>{{ won(cost.refuel_cost) }}</strong>
    </div>
    <div>
      <span>카드 할인</span>
      <strong class="saving">-{{ won(cost.card_discount_amount) }}</strong>
    </div>
    <div>
      <span>이동 비용</span>
      <strong>{{ won(cost.travel_cost) }}</strong>
    </div>
    <div class="total">
      <span>최종 비용</span>
      <strong>{{ won(cost.effective_total_cost) }}</strong>
    </div>
  </div>
</template>

