<script setup>
import { LocateFixed, MapPin, Search, X } from "@lucide/vue";
import { ref, watch, onMounted } from "vue";
import { geocode, presets } from "../utils/geocoder";
import { apiRequest } from "../api/client";

const model = defineModel({ required: true });
const loading = ref(false);
const message = ref("");
const searchQuery = ref("");
const searchResults = ref([]);
const selectedLocationName = ref("");
const showDropdown = ref(false);

// 초기 위경도 기반으로 출발 위치명 동기화
onMounted(() => {
  if (model.value) {
    const found = presets.find(
      p => Math.abs(p.latitude - model.value.latitude) < 0.001 &&
           Math.abs(p.longitude - model.value.longitude) < 0.001
    );
    selectedLocationName.value = found ? found.name : "역삼역/강남역 부근 (기본값)";
  }
});

function applyPreset(preset) {
  model.value = {
    latitude: preset.latitude,
    longitude: preset.longitude
  };
  selectedLocationName.value = preset.name;
  searchQuery.value = "";
  searchResults.value = [];
  showDropdown.value = false;
  message.value = `출발지가 '${preset.name}'(으)로 변경되었습니다.`;
}

let debounceTimer = null;

function handleInput() {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }

  const query = searchQuery.value.trim();
  if (!query) {
    searchResults.value = [];
    showDropdown.value = false;
    return;
  }

  // Pre-populate with local geocode search results immediately for instant feedback
  searchResults.value = geocode(query);
  showDropdown.value = searchResults.value.length > 0;

  loading.value = true;
  debounceTimer = setTimeout(async () => {
    try {
      const response = await apiRequest(`/stations/geocode/?query=${encodeURIComponent(query)}`);
      if (response && Array.isArray(response.results)) {
        searchResults.value = response.results;
        showDropdown.value = searchResults.value.length > 0;
      }
    } catch (err) {
      console.error("Geocoding proxy search failed:", err);
      // Fallback is already loaded via geocode(query)
    } finally {
      loading.value = false;
    }
  }, 300);
}

function clearSearch() {
  searchQuery.value = "";
  searchResults.value = [];
  showDropdown.value = false;
}

function useBrowserLocation() {
  message.value = "";
  if (!navigator.geolocation) {
    message.value = "브라우저 위치 기능을 사용할 수 없습니다.";
    return;
  }

  loading.value = true;
  navigator.geolocation.getCurrentPosition(
    (position) => {
      model.value = {
        latitude: Number(position.coords.latitude.toFixed(6)),
        longitude: Number(position.coords.longitude.toFixed(6))
      };
      selectedLocationName.value = "내 현재 GPS 위치";
      loading.value = false;
      message.value = "현재 위치가 성공적으로 감지되었습니다.";
    },
    () => {
      loading.value = false;
      message.value = "위치 권한을 확인하거나 아래 추천 검색을 이용해 주세요.";
    },
    { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
  );
}
</script>

<template>
  <section class="panel">
    <div class="panelHeader">
      <div>
        <p class="eyebrow">Location Settings</p>
        <h2>출발 위치 검색</h2>
      </div>
      <button class="iconButton" type="button" title="내 GPS 위치 사용" :disabled="loading" @click="useBrowserLocation">
        <LocateFixed :size="18" />
      </button>
    </div>

    <!-- Active Departure Location Badge -->
    <div class="activeLocationBadge">
      <MapPin :size="16" class="neonText" style="color: var(--primary);" />
      <div class="info">
        <span class="label">선택된 출발지</span>
        <span class="value">{{ selectedLocationName }}</span>
      </div>
    </div>

    <!-- Address Search Input -->
    <div class="searchControl">
      <span class="inputLabel">출발지 주소 또는 랜드마크 검색</span>
      <div class="searchInputWrapper">
        <Search class="searchIcon" :size="16" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="예: 서울시청, 강남역, 대전시청, 부산역..."
          @input="handleInput"
          @focus="handleInput"
        />
        <button v-if="searchQuery" class="clearButton" type="button" @click="clearSearch">
          <X :size="14" />
        </button>
      </div>

      <!-- Realtime Autocomplete Dropdown -->
      <transition name="fadeSlide">
        <div v-if="showDropdown" class="searchDropdown">
          <button
            v-for="item in searchResults"
            :key="item.name"
            class="dropdownItem"
            type="button"
            @click="applyPreset(item)"
          >
            <div class="itemMain">
              <MapPin :size="14" style="margin-right: 6px; color: var(--primary);" />
              <strong>{{ item.name }}</strong>
            </div>
            <span class="itemSub">{{ item.address }}</span>
          </button>
        </div>
      </transition>
    </div>

    <!-- Quick Location Presets -->
    <div class="presetSection">
      <span class="presetLabel">주요 출발지 퀵 선택</span>
      <div class="locationPresets">
        <button
          v-for="preset in presets.slice(0, 5)"
          :key="preset.name"
          class="presetLocBtn"
          type="button"
          :class="{ active: selectedLocationName === preset.name }"
          @click="applyPreset(preset)"
        >
          {{ preset.name }}
        </button>
      </div>
    </div>

    <!-- Hidden native coords input to keep Vue data-binding working behind the scenes -->
    <div style="display: none;">
      <input v-model.number="model.latitude" type="number" />
      <input v-model.number="model.longitude" type="number" />
    </div>

    <p v-if="message" class="hintText success" style="margin-top: 10px;">{{ message }}</p>
  </section>
</template>

<style scoped>
.activeLocationBadge {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 18px;
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.05);
}
.activeLocationBadge .info {
  display: flex;
  flex-direction: column;
}
.activeLocationBadge .info .label {
  font-size: 10px;
  color: var(--slate-400);
  text-transform: uppercase;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.activeLocationBadge .info .value {
  font-size: 14px;
  font-weight: 800;
  color: var(--secondary);
  margin-top: 2px;
}
.searchControl {
  position: relative;
  margin-bottom: 18px;
}
.inputLabel {
  font-size: 11px;
  font-weight: 800;
  color: var(--slate-400);
  text-transform: uppercase;
  display: block;
  margin-bottom: 8px;
}
.searchInputWrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.searchIcon {
  position: absolute;
  left: 14px;
  color: var(--slate-400);
  pointer-events: none;
}
.searchInputWrapper input {
  width: 100%;
  padding: 12px 16px 12px 40px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: var(--slate-100);
  font-size: 13.5px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.searchInputWrapper input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.2), inset 0 1px 1px rgba(255,255,255,0.05);
  background: rgba(0, 0, 0, 0.35);
}
.clearButton {
  position: absolute;
  right: 14px;
  background: transparent;
  border: none;
  color: var(--slate-400);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border-radius: 50%;
  transition: all 0.2s;
}
.clearButton:hover {
  color: var(--slate-100);
  background: rgba(255, 255, 255, 0.1);
}
.searchDropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: rgba(26, 38, 34, 0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.4), 0 0 1px rgba(255,255,255,0.1);
  z-index: 99;
  max-height: 240px;
  overflow-y: auto;
  padding: 6px;
}
.dropdownItem {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 10px 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--slate-200);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}
.dropdownItem:hover {
  background: rgba(0, 229, 255, 0.08);
  color: var(--secondary);
}
.dropdownItem .itemMain {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
}
.dropdownItem .itemSub {
  font-size: 11px;
  color: var(--slate-400);
  margin-top: 3px;
  margin-left: 20px;
}
.presetSection {
  margin-top: 16px;
}
.presetLabel {
  font-size: 11px;
  font-weight: 800;
  color: var(--slate-400);
  text-transform: uppercase;
  display: block;
  margin-bottom: 8px;
}
.presetLocBtn {
  font-size: 11.5px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  color: var(--slate-300);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.presetLocBtn:hover, .presetLocBtn.active {
  background: rgba(0, 229, 255, 0.12);
  border-color: var(--primary);
  color: var(--secondary);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.15);
}

.fadeSlide-enter-active, .fadeSlide-enter-active {
  transition: all 0.2s ease;
}
.fadeSlide-enter-from, .fadeSlide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
