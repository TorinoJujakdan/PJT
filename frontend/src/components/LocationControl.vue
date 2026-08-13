<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { BriefcaseBusiness, Home, LoaderCircle, LocateFixed, MapPin, Search, X } from "@lucide/vue";
import { reverseGeocodeLocation, searchLocations } from "../api/stations";
import { loadNaverMapsScript } from "../utils/naverMapLoader";

const model = defineModel({ required: true });

const PRESET_STORAGE_KEYS = {
  home: "smartfuel_preset_home",
  work: "smartfuel_preset_work"
};
const RECENT_STORAGE_KEY = "smartfuel_recent_locations";
const MAX_RECENT_LOCATIONS = 5;

const loading = ref(false);
const locating = ref(false);
const message = ref("");
const messageType = ref("info");
const searchQuery = ref("");
const searchResults = ref([]);
const showDropdown = ref(false);
const recentLocations = ref(readRecentLocations());
const presets = ref({
  home: readStoredLocation(PRESET_STORAGE_KEYS.home),
  work: readStoredLocation(PRESET_STORAGE_KEYS.work)
});
const activePresetEditor = ref(null);

let debounceTimer = null;
let reverseTimer = null;
let lastResolvedKey = "";
let searchRequestId = 0;
let reverseRequestId = 0;

function isCoordinateValue(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

const activeName = computed(() => model.value?.name || model.value?.address || "출발지 미확정");
const activeAddress = computed(() => model.value?.address || "좌표를 먼저 확정해 주세요.");
const activeCoords = computed(() => {
  if (!isCoordinateValue(model.value?.latitude) || !isCoordinateValue(model.value?.longitude)) {
    return "";
  }
  const latitude = Number(model.value.latitude);
  const longitude = Number(model.value.longitude);
  return `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
});
const activeAccuracy = computed(() => {
  const accuracy = Number(model.value?.accuracy_m);
  if (!Number.isFinite(accuracy)) return "";
  return `${Math.round(accuracy).toLocaleString("ko-KR")}m`;
});

function coordsKey(latitude, longitude) {
  return `${Number(latitude).toFixed(6)},${Number(longitude).toFixed(6)}`;
}

function normalizeStoredLocation(item, fallbackName = "저장된 위치") {
  if (!item || !isCoordinateValue(item.latitude) || !isCoordinateValue(item.longitude)) {
    return null;
  }

  return {
    latitude: Number(item.latitude),
    longitude: Number(item.longitude),
    name: item.name || item.address || fallbackName,
    address: item.address || item.road_address || item.jibun_address || "",
    road_address: item.road_address || "",
    jibun_address: item.jibun_address || "",
    source: item.source || "stored",
    accuracy_m: item.accuracy_m ?? null,
    saved_at: item.saved_at || new Date().toISOString()
  };
}

function readStoredLocation(key) {
  try {
    return normalizeStoredLocation(JSON.parse(window.localStorage.getItem(key)));
  } catch (_error) {
    window.localStorage.removeItem(key);
    return null;
  }
}

function writeStoredLocation(key, item) {
  const normalized = normalizeStoredLocation(item);
  if (!normalized) return null;

  const saved = {
    ...normalized,
    saved_at: new Date().toISOString()
  };
  window.localStorage.setItem(key, JSON.stringify(saved));
  return saved;
}

function readRecentLocations() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(RECENT_STORAGE_KEY));
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => normalizeStoredLocation(item))
      .filter(Boolean)
      .slice(0, MAX_RECENT_LOCATIONS);
  } catch (_error) {
    window.localStorage.removeItem(RECENT_STORAGE_KEY);
    return [];
  }
}

function writeRecentLocations(items) {
  window.localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(items));
}

function rememberRecentLocation(item) {
  const normalized = normalizeStoredLocation(item);
  if (!normalized) return;

  const key = coordsKey(normalized.latitude, normalized.longitude);
  recentLocations.value = [
    { ...normalized, saved_at: new Date().toISOString() },
    ...recentLocations.value.filter((recent) => coordsKey(recent.latitude, recent.longitude) !== key)
  ].slice(0, MAX_RECENT_LOCATIONS);
  writeRecentLocations(recentLocations.value);
}

function removeRecentLocation(item) {
  const key = coordsKey(item.latitude, item.longitude);
  recentLocations.value = recentLocations.value.filter(
    (recent) => coordsKey(recent.latitude, recent.longitude) !== key
  );
  writeRecentLocations(recentLocations.value);
  setMessage("최근 위치 태그를 삭제했습니다.", "success");
}

function setMessage(text, type = "info") {
  message.value = text;
  messageType.value = type;
}

function updateLocation(item, { remember = true } = {}) {
  const latitude = Number(item.latitude);
  const longitude = Number(item.longitude);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    return;
  }

  lastResolvedKey = coordsKey(latitude, longitude);
  Object.assign(model.value, {
    latitude,
    longitude,
    name: item.name || item.address || "선택한 위치",
    address: item.address || item.road_address || item.jibun_address || "",
    road_address: item.road_address || "",
    jibun_address: item.jibun_address || "",
    source: item.source || "manual",
    accuracy_m: item.accuracy_m ?? null
  });

  if (remember) {
    rememberRecentLocation(model.value);
  }
}

function normalizedResults(results) {
  return (results || [])
    .map((item) => ({
      ...item,
      latitude: Number(item.latitude),
      longitude: Number(item.longitude)
    }))
    .filter((item) => Number.isFinite(item.latitude) && Number.isFinite(item.longitude));
}

function geocodeWithNaverMapScript(query) {
  return loadNaverMapsScript()
    .then((naverMaps) => new Promise((resolve) => {
      if (!naverMaps.Service?.geocode) {
        resolve([]);
        return;
      }
      naverMaps.Service.geocode({ query, address: query }, (status, response) => {
        if (status !== naverMaps.Service.Status.OK) {
          resolve([]);
          return;
        }
        const v2Addresses = response?.v2?.addresses || [];
        const legacyItems = response?.result?.items || [];
        const mappedV2 = v2Addresses.map((address) => {
          const roadAddress = address.roadAddress || "";
          const jibunAddress = address.jibunAddress || "";
          const displayAddress = roadAddress || jibunAddress;
          return {
            name: displayAddress || query,
            address: displayAddress,
            road_address: roadAddress,
            jibun_address: jibunAddress,
            latitude: address.y,
            longitude: address.x,
            source: "naver_maps_js_geocode"
          };
        });
        const mappedLegacy = legacyItems.map((item) => {
          const roadAddress = item.address || "";
          const jibunAddress = item.addrdetail
            ? [
                item.addrdetail.sido,
                item.addrdetail.sigugun,
                item.addrdetail.dongmyun,
                item.addrdetail.ri,
                item.addrdetail.rest
              ].filter(Boolean).join(" ")
            : "";
          const displayAddress = roadAddress || jibunAddress;
          return {
            name: displayAddress || query,
            address: displayAddress,
            road_address: roadAddress,
            jibun_address: jibunAddress,
            latitude: item.point?.y,
            longitude: item.point?.x,
            source: "naver_maps_js_geocode"
          };
        });
        resolve(normalizedResults([...mappedV2, ...mappedLegacy]));
      });
    }))
    .catch(() => []);
}

async function resolveLocationSearch(query) {
  try {
    const response = await searchLocations(query);
    const backendResults = normalizedResults(response.results);
    if (backendResults.length) {
      return backendResults;
    }
  } catch (_error) {
    // Fall through to the browser-side Naver Maps geocoder below.
  }
  return geocodeWithNaverMapScript(query);
}

function handleInput() {
  window.clearTimeout(debounceTimer);

  const query = searchQuery.value.trim();
  if (query.length < 2) {
    loading.value = false;
    searchResults.value = [];
    showDropdown.value = false;
    return;
  }

  showDropdown.value = true;
  loading.value = true;
  const requestId = ++searchRequestId;
  debounceTimer = window.setTimeout(async () => {
    try {
      const results = await resolveLocationSearch(query);
      if (requestId !== searchRequestId) return;
      searchResults.value = results;
      if (!searchResults.value.length) {
        setMessage("검색 결과가 없습니다.", "info");
      }
    } catch (error) {
      if (requestId !== searchRequestId) return;
      searchResults.value = [];
      setMessage(error.message || "위치 검색을 완료하지 못했습니다.", "error");
    } finally {
      if (requestId === searchRequestId) {
        loading.value = false;
      }
    }
  }, 300);
}

async function searchNow() {
  window.clearTimeout(debounceTimer);
  const query = searchQuery.value.trim();
  if (query.length < 2) {
    searchResults.value = [];
    showDropdown.value = false;
    return [];
  }

  showDropdown.value = true;
  loading.value = true;
  const requestId = ++searchRequestId;
  try {
    const results = await resolveLocationSearch(query);
    if (requestId !== searchRequestId) return searchResults.value;
    searchResults.value = results;
    if (!searchResults.value.length) {
      setMessage("검색 결과가 없습니다.", "info");
    }
    return searchResults.value;
  } catch (error) {
    if (requestId !== searchRequestId) return searchResults.value;
    searchResults.value = [];
    setMessage(error.message || "검색 중 오류가 발생했습니다.", "error");
    return [];
  } finally {
    if (requestId === searchRequestId) {
      loading.value = false;
    }
  }
}

async function submitSearch() {
  const results = searchResults.value.length ? searchResults.value : await searchNow();
  if (results.length) {
    applySearchResult(results[0]);
  }
}

function applySearchResult(item) {
  updateLocation(item);
  searchQuery.value = item.name || item.address || "";
  searchResults.value = [];
  showDropdown.value = false;
  setMessage("출발지가 확정되었습니다.", "success");
}

function applyStoredLocation(item, label = "저장된 위치") {
  updateLocation({ ...item, source: item.source || "stored" });
  searchQuery.value = item.name || item.address || "";
  searchResults.value = [];
  showDropdown.value = false;
  setMessage(`${label}로 출발지가 변경되었습니다.`, "success");
}

function clearSearch() {
  window.clearTimeout(debounceTimer);
  searchRequestId++;
  searchQuery.value = "";
  searchResults.value = [];
  showDropdown.value = false;
  loading.value = false;
}

async function resolveAddress(latitude, longitude, fallbackName = "선택한 위치") {
  const requestId = ++reverseRequestId;
  try {
    const response = await reverseGeocodeLocation(latitude, longitude);
    if (requestId !== reverseRequestId) return false;
    if (response.result) {
      updateLocation({
        ...response.result,
        name: response.result.name || fallbackName
      });
      return true;
    }
  } catch (error) {
    if (requestId !== reverseRequestId) return false;
    setMessage(error.message || "주소 확인을 완료하지 못했습니다.", "error");
  }
  return false;
}

function useBrowserLocation() {
  message.value = "";
  if (!navigator.geolocation) {
    setMessage("브라우저 위치 기능을 사용할 수 없습니다.", "error");
    return;
  }

  locating.value = true;
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const latitude = Number(position.coords.latitude.toFixed(6));
      const longitude = Number(position.coords.longitude.toFixed(6));
      updateLocation({
        latitude,
        longitude,
        name: "현재 위치 확인 중",
        address: "",
        source: "browser_geolocation",
        accuracy_m: position.coords.accuracy
      });
      const resolved = await resolveAddress(latitude, longitude, "현재 위치");
      setMessage(resolved ? "현재 위치가 확정되었습니다." : "현재 좌표가 확정되었습니다.", "success");
      locating.value = false;
    },
    () => {
      locating.value = false;
      setMessage("위치 권한을 확인해 주세요.", "error");
    },
    { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 }
  );
}

function getPresetLabel(type) {
  return type === "home" ? "집" : "회사";
}

function savePreset(type) {
  const label = getPresetLabel(type);
  const saved = writeStoredLocation(PRESET_STORAGE_KEYS[type], {
    ...model.value,
    source: `${type}_preset`
  });
  if (!saved) {
    setMessage("먼저 출발지를 확정해 주세요.", "error");
    return false;
  }
  presets.value = {
    ...presets.value,
    [type]: saved
  };
  setMessage(`${label} 위치로 저장했습니다.`, "success");
  return true;
}

function openPresetEditor(type = "home") {
  activePresetEditor.value = type;
}

function closePresetEditor() {
  activePresetEditor.value = null;
}

function confirmPresetSave(type) {
  if (savePreset(type)) {
    closePresetEditor();
  }
}

function usePreset(type) {
  const label = getPresetLabel(type);
  const preset = presets.value[type];
  if (!preset) {
    openPresetEditor(type);
    setMessage(`${label} 주소를 먼저 등록해 주세요.`, "info");
    return;
  }
  applyStoredLocation(preset, label);
}


watch(
  () => [
    model.value?.latitude,
    model.value?.longitude,
    model.value?.name,
    model.value?.address
  ],
  ([latitude, longitude, name, address]) => {
    if (!isCoordinateValue(latitude) || !isCoordinateValue(longitude)) {
      searchQuery.value = "";
      return;
    }

    const key = coordsKey(latitude, longitude);
    if (key !== lastResolvedKey) {
      lastResolvedKey = key;
    }

    // Sync the searchQuery input text so that the input reflects the current active location,
    // but only if the dropdown is not open (so we don't disrupt the user's active typing)
    const displayName = name || address || "";
    if (!showDropdown.value && searchQuery.value !== displayName) {
      searchQuery.value = displayName;
    }
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  window.clearTimeout(debounceTimer);
  window.clearTimeout(reverseTimer);
});
</script>

<template>
  <section class="panel locationPanel">
    <div class="panelHeader">
      <div>
        <p class="eyebrow">Location</p>
        <h2>출발 위치</h2>
      </div>
      <button class="iconButton" type="button" title="현재 위치 사용" :disabled="locating" @click="useBrowserLocation">
        <LoaderCircle v-if="locating" :size="18" class="spinIcon" />
        <LocateFixed v-else :size="18" />
      </button>
    </div>

    <div class="presetActions" aria-label="집 회사 빠른 출발지 선택">
      <div class="presetQuickTabs twoTabs">
        <button
          class="presetQuickTab"
          type="button"
          :class="{ saved: presets.home }"
          :title="presets.home ? '집 주소를 출발 위치로 설정' : '집 주소 등록 탭 열기'"
          @click="usePreset('home')"
        >
          <Home :size="15" />
          <span>집</span>
        </button>
        <button
          class="presetQuickTab"
          type="button"
          :class="{ saved: presets.work }"
          :title="presets.work ? '회사 주소를 출발 위치로 설정' : '회사 주소 등록 탭 열기'"
          @click="usePreset('work')"
        >
          <BriefcaseBusiness :size="15" />
          <span>회사</span>
        </button>
      </div>

      <div class="presetEditLinks" aria-label="집 회사 등록 수정">
        <button type="button" @click="openPresetEditor('home')">
          집 {{ presets.home ? "수정" : "등록" }}
        </button>
        <button type="button" @click="openPresetEditor('work')">
          회사 {{ presets.work ? "수정" : "등록" }}
        </button>
      </div>

      <div v-if="activePresetEditor" class="presetEditorPanel" role="tabpanel" aria-label="장소 등록 수정 탭">
        <div class="presetEditorHeader">
          <strong>장소 등록/수정</strong>
          <button type="button" class="presetEditorClose" aria-label="장소 등록 탭 닫기" @click="closePresetEditor">
            <X :size="13" />
          </button>
        </div>
        <div class="presetEditorTabs" role="tablist" aria-label="등록할 장소 선택">
          <button
            type="button"
            role="tab"
            :aria-selected="activePresetEditor === 'home'"
            :class="{ active: activePresetEditor === 'home' }"
            @click="openPresetEditor('home')"
          >
            집
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="activePresetEditor === 'work'"
            :class="{ active: activePresetEditor === 'work' }"
            @click="openPresetEditor('work')"
          >
            회사
          </button>
        </div>
        <p class="presetEditorCopy">
          현재 선택된 출발 위치를 {{ getPresetLabel(activePresetEditor) }} 주소로 저장합니다.
        </p>
        <button class="presetEditorSave" type="button" @click="confirmPresetSave(activePresetEditor)">
          현재 위치를 {{ getPresetLabel(activePresetEditor) }}으로 저장
        </button>
      </div>
    </div>

    <div class="searchControl">
      <label class="inputLabel" for="departure-search">주소 검색</label>
      <div class="searchInputWrapper">
        <Search class="searchIcon" :size="16" />
        <input
          id="departure-search"
          v-model="searchQuery"
          type="text"
          autocomplete="off"
          placeholder="도로명 주소, 지번, 건물명"
          @input="handleInput"
          @focus="handleInput"
          @keydown.enter.prevent="submitSearch"
          @keydown.escape="clearSearch"
        />
        <button v-if="searchQuery" class="clearButton" type="button" title="검색어 지우기" @click="clearSearch">
          <X :size="14" />
        </button>
      </div>

      <transition name="fadeSlide">
        <div v-if="showDropdown" class="searchDropdown">
          <div v-if="loading" class="dropdownState">
            <LoaderCircle :size="15" class="spinIcon" />
            <span>검색 중</span>
          </div>
          <div v-else-if="!searchResults.length" class="dropdownState">
            <span>검색 결과 없음</span>
          </div>
          <template v-else>
            <button
              v-for="item in searchResults"
              :key="`${item.latitude}-${item.longitude}-${item.address}`"
              class="dropdownItem"
              type="button"
              @click="applySearchResult(item)"
            >
              <MapPin :size="15" />
              <span>
                <strong>{{ item.name }}</strong>
                <small>{{ item.address || item.road_address || item.jibun_address }}</small>
              </span>
            </button>
          </template>
        </div>
      </transition>
    </div>

    <div class="activeLocationBadge" aria-live="polite">
      <MapPin :size="18" />
      <div class="activeLocationText">
        <small class="locationSectionLabel">선택된 출발 위치</small>
        <strong>{{ activeName }}</strong>
        <span>{{ activeAddress }}</span>
        <small v-if="activeCoords">{{ activeCoords }}<template v-if="activeAccuracy"> · 정확도 {{ activeAccuracy }}</template></small>
      </div>
    </div>

    <div v-if="recentLocations.length" class="recentList" aria-label="최근 위치 바로가기">
      <div class="locationSectionLabel recentListTitle">최근 검색 위치</div>
      <div
        v-for="item in recentLocations"
        :key="`${item.latitude}-${item.longitude}-${item.saved_at}`"
        class="recentItem"
      >
        <button
          class="recentItemSelect"
          type="button"
          :title="`${item.name || item.address} 위치로 설정`"
          @click="applyStoredLocation(item, '최근 위치')"
        >
          <MapPin :size="13" />
          <span>{{ item.name || item.address }}</span>
        </button>
        <button
          class="recentItemRemove"
          type="button"
          :aria-label="`${item.name || item.address} 최근 위치 삭제`"
          title="최근 위치 삭제"
          @click="removeRecentLocation(item)"
        >
          <X :size="12" />
        </button>
      </div>
    </div>


    <input v-model.number="model.latitude" type="hidden" />
    <input v-model.number="model.longitude" type="hidden" />

    <p v-if="message" class="hintText" :class="messageType">{{ message }}</p>
  </section>
</template>

<style scoped src="./LocationControl.css"></style>
