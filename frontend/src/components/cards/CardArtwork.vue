<script setup>
import { ref } from "vue";
import { CreditCard } from "@lucide/vue";

defineProps({
  src: { type: String, default: "" },
  alt: { type: String, required: true },
});

const failed = ref(false);
</script>

<template>
  <div class="cardArtwork" aria-hidden="true">
    <img v-if="src && !failed" :src="src" :alt="alt" @error="failed = true" />
    <CreditCard v-else :size="30" />
  </div>
</template>
