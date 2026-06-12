<script setup>
import { Search, Plus, WalletCards } from "@lucide/vue";
import CatalogCardPanel from "../components/cards/CatalogCardPanel.vue";
import ManualCardPanel from "../components/cards/ManualCardPanel.vue";
import SavedCardsPanel from "../components/cards/SavedCardsPanel.vue";
import { cardsWorkspaceStore } from "../stores/cardsWorkspaceStore";

defineProps({
  cards: { type: Array, default: () => [] },
});
const emit = defineEmits(["changed"]);

const tabs = [
  { id: "catalog", label: "카드 검색", icon: Search },
  { id: "manual", label: "직접 등록", icon: Plus },
  { id: "saved", label: "내 카드", icon: WalletCards },
];
</script>

<template>
  <main class="cardsWorkspace">
    <nav class="cardsTabs" aria-label="카드 관리 메뉴">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        :class="{ active: cardsWorkspaceStore.activeTab === tab.id }"
        :aria-current="cardsWorkspaceStore.activeTab === tab.id ? 'page' : undefined"
        @click="cardsWorkspaceStore.activeTab = tab.id"
      >
        <component :is="tab.icon" :size="19" aria-hidden="true" />
        <span>{{ tab.label }}</span>
        <small v-if="tab.id === 'saved'">{{ cards.length }}</small>
      </button>
    </nav>

    <div class="cardsPrimaryScroll">
      <CatalogCardPanel
        v-if="cardsWorkspaceStore.activeTab === 'catalog'"
        @changed="emit('changed')"
      />
      <ManualCardPanel
        v-else-if="cardsWorkspaceStore.activeTab === 'manual'"
        @changed="emit('changed')"
      />
      <SavedCardsPanel
        v-else
        :cards="cards"
        @changed="emit('changed')"
        @go-manual="cardsWorkspaceStore.activeTab = 'manual'"
      />
    </div>
  </main>
</template>
