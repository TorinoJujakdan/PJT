<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { AlertTriangle, LocateFixed, Minus, Plus } from "@lucide/vue";
import { loadNaverMapsScript } from "../utils/naverMapLoader";

const props = defineProps({
  recommendation: {
    type: Object,
    default: null
  },
  candidates: {
    type: Array,
    default: () => []
  },
  selectedStationId: {
    type: [Number, String],
    default: null
  },
  userLocation: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(["select", "location-select", "map-click"]);

const mapElement = ref(null);
const mapState = ref("idle");
const fallbackReason = ref("");

let map = null;
let naverMaps = null;
let markers = [];
let markerByStationId = new Map();
let routeLine = null; // 출발지와 추천 주유소를 잇는 최적 경로 라인
let userMarker = null;
let infoWindow = null;
let authFailureTimer = null;
let authFailureChecks = 0;
let lastBoundsKey = "";
let lastUserLocationKey = "";
const routeFallbackReason = ref("");

// 중복 제거된 후보 주유소들 목록
const displayCandidates = computed(() => {
  const seen = new Set();
  const rawList = [];
  if (props.recommendation) rawList.push(props.recommendation);
  if (props.candidates && props.candidates.length) rawList.push(...props.candidates);

  return rawList.filter((candidate) => {
    const station = candidate?.station;
    if (!station?.station_id || seen.has(station.station_id)) {
      return false;
    }
    seen.add(station.station_id);
    return Number.isFinite(Number(station.latitude)) && Number.isFinite(Number(station.longitude));
  });
});

const activeStationId = computed(() => props.selectedStationId || props.recommendation?.station?.station_id);

function stationIdKey(stationId) {
  return stationId === null || stationId === undefined ? "" : String(stationId);
}

const activeCandidate = computed(() => {
  return displayCandidates.value.find((candidate) => stationIdKey(candidate.station.station_id) === stationIdKey(activeStationId.value)) || null;
});

const hasUserLocation = computed(() => {
  return (
    props.userLocation?.latitude !== null &&
    props.userLocation?.latitude !== undefined &&
    props.userLocation?.latitude !== "" &&
    props.userLocation?.longitude !== null &&
    props.userLocation?.longitude !== undefined &&
    props.userLocation?.longitude !== "" &&
    Number.isFinite(Number(props.userLocation.latitude)) &&
    Number.isFinite(Number(props.userLocation.longitude))
  );
});

// 커스텀 주유소 마커 HTML
function markerIcon(candidate, isRecommended, isActive) {
  const station = candidate.station;
  // 주유 카드 할인을 직접 반영한 예상가 계산
  const basePrice = station.fuel_price_per_liter || 0;
  const discountAmount = candidate.cost_breakdown?.card_discount_amount || 0;
  const liters = candidate.cost_breakdown?.target_liters || 1;
  const price = Math.max(0, Math.round(basePrice - (discountAmount / liters)));

  const brandNames = {
    SK: "SK",
    GS: "GS",
    S_OIL: "S-OIL",
    HD_HYUNDAI: "현대",
    ALDEUL: "알뜰"
  };
  const brandLabel = brandNames[station.brand] || station.brand || "주유소";

  return {
    content: `<button class="mapMarker${isRecommended ? " recommended" : ""}${isActive ? " active" : ""}" type="button" aria-label="주유소 선택">
                <span class="brandBadge">${brandLabel}</span>
                <span class="priceText">${price.toLocaleString()}원</span>
              </button>`,
    anchor: new naverMaps.Point(40, 20)
  };
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function won(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number).toLocaleString("ko-KR")}원` : "-";
}

function closeInfoWindow() {
  if (infoWindow) {
    infoWindow.close();
    infoWindow = null;
  }
}

function infoWindowContent(candidate) {
  const station = candidate?.station || {};
  const cost = candidate?.cost_breakdown || {};
  return `
    <section class="mapInfoWindow" aria-label="선택 주유소 상세">
      <strong>${escapeHtml(station.name || "선택한 주유소")}</strong>
      <span>${escapeHtml(station.address || "주소 정보 없음")}</span>
      <dl>
        <div><dt>리터당</dt><dd>${won(station.fuel_price_per_liter)}</dd></div>
        <div><dt>거리</dt><dd>${escapeHtml(station.distance_km ?? "-")} km</dd></div>
        <div><dt>최종비용</dt><dd>${won(cost.effective_total_cost)}</dd></div>
      </dl>
    </section>`;
}

function openInfoWindow(candidate, marker) {
  if (!map || !naverMaps || !candidate || !marker) return;
  closeInfoWindow();
  infoWindow = new naverMaps.InfoWindow({
    content: infoWindowContent(candidate),
    borderWidth: 0,
    backgroundColor: "transparent",
    disableAnchor: false,
    pixelOffset: new naverMaps.Point(0, -8)
  });
  infoWindow.open(map, marker);
}

function openInfoWindowForStation(stationId) {
  const candidate = displayCandidates.value.find((item) => stationIdKey(item.station.station_id) === stationIdKey(stationId));
  const marker = markerByStationId.get(stationIdKey(stationId));
  openInfoWindow(candidate, marker);
}

function stationLatLng(station) {
  return new naverMaps.LatLng(Number(station.latitude), Number(station.longitude));
}

function routePathLatLngs(station) {
  return (station?.route_path || [])
    .map((point) => ({
      latitude: Number(point.latitude),
      longitude: Number(point.longitude)
    }))
    .filter((point) => Number.isFinite(point.latitude) && Number.isFinite(point.longitude))
    .map((point) => new naverMaps.LatLng(point.latitude, point.longitude));
}

function candidateHasRoutePath(candidate) {
  return routePathLatLngs(candidate?.station).length >= 2;
}

function routeCandidateForLine() {
  if (candidateHasRoutePath(activeCandidate.value)) {
    return activeCandidate.value;
  }
  if (candidateHasRoutePath(props.recommendation)) {
    return props.recommendation;
  }
  return null;
}

function userLocationKey() {
  if (!hasUserLocation.value) return "";
  return `${Number(props.userLocation.latitude).toFixed(6)},${Number(props.userLocation.longitude).toFixed(6)}`;
}

function boundsKey() {
  const stationKey = displayCandidates.value
    .map((candidate) => candidate.station.station_id)
    .join(",");
  return `${userLocationKey()}|${stationKey}|${props.recommendation?.station?.station_id || ""}`;
}

// 1. 주유소 마커 렌더링
function renderMarkers() {
  if (!map || !naverMaps) return;

  closeInfoWindow();
  markers.forEach((marker) => marker.setMap(null));
  markerByStationId = new Map();
  markers = displayCandidates.value.map((candidate) => {
    const station = candidate.station;
    const isRecommended = stationIdKey(station.station_id) === stationIdKey(props.recommendation?.station?.station_id);
    const isActive = stationIdKey(station.station_id) === stationIdKey(activeStationId.value);

    const marker = new naverMaps.Marker({
      position: stationLatLng(station),
      map,
      title: station.name,
      icon: markerIcon(candidate, isRecommended, isActive),
      zIndex: isActive ? 20 : isRecommended ? 10 : 1
    });

    naverMaps.Event.addListener(marker, "click", () => {
      emit("select", station.station_id);
      openInfoWindow(candidate, marker);
    });

    markerByStationId.set(stationIdKey(station.station_id), marker);
    return marker;
  });
}

// 2. 출발 위치 마커 렌더링
function renderUserMarker() {
  if (!map || !naverMaps || !hasUserLocation.value) {
    if (userMarker) {
      userMarker.setMap(null);
      userMarker = null;
    }
    return;
  }

  const pos = new naverMaps.LatLng(Number(props.userLocation.latitude), Number(props.userLocation.longitude));

  if (userMarker) {
    userMarker.setPosition(pos);
  } else {
    userMarker = new naverMaps.Marker({
      position: pos,
      map,
      title: "출발 위치",
      icon: {
        content: `<div class="userLocationMarker">
                    <div class="pulse"></div>
                    <div class="dot"></div>
                  </div>`,
        anchor: new naverMaps.Point(12, 12)
      },
      zIndex: 100
    });
  }
}

// 3. 출발지 ~ BEST 추천 주유소 파란색 실시간 경로선(Route Line) 렌더링
function renderRouteLine() {
  if (!map || !naverMaps) return;
  routeFallbackReason.value = "";

  // 기존 경로선 삭제
  if (routeLine) {
    routeLine.setMap(null);
    routeLine = null;
  }

  // Draw only an actual Directions route path; do not fall back to a straight line.
  if (hasUserLocation.value && displayCandidates.value.length) {
    const routeCandidate = routeCandidateForLine();
    const path = routePathLatLngs(routeCandidate?.station);
    if (path.length < 2) {
      routeFallbackReason.value = "실제 주행 경로가 없는 후보는 직선 경로를 표시하지 않습니다.";
      return;
    }

    routeLine = new naverMaps.Polyline({
      map,
      path,
      strokeColor: "#0ea5e9",
      strokeOpacity: 0.8,
      strokeWeight: 6,
      strokeStyle: "solid",
      strokeLineCap: "round",
      strokeLineJoin: "round"
    });
  }
}

// 4. 모든 마커가 잘 보이도록 지도 중심 및 줌 자동 조정
function adjustMapBounds() {
  if (!map || !naverMaps) return;

  const bounds = new naverMaps.LatLngBounds();
  let pointsAdded = 0;

  if (hasUserLocation.value) {
    bounds.extend(new naverMaps.LatLng(Number(props.userLocation.latitude), Number(props.userLocation.longitude)));
    pointsAdded++;
  }

  displayCandidates.value.forEach((candidate) => {
    bounds.extend(stationLatLng(candidate.station));
    pointsAdded++;
  });

  if (pointsAdded > 0) {
    map.fitBounds(bounds, {
      top: 100,
      right: 100,
      bottom: 100,
      left: 100
    });
  }
}

// 지도 제어 함수들 (우측 상단 퀵 버튼)
function zoomIn() {
  if (!map) return;
  map.setZoom(map.getZoom() + 1, true);
}

function zoomOut() {
  if (!map) return;
  map.setZoom(map.getZoom() - 1, true);
}

function focusOnUser() {
  if (!map || !naverMaps || !hasUserLocation.value) return;
  const pos = new naverMaps.LatLng(Number(props.userLocation.latitude), Number(props.userLocation.longitude));
  map.panTo(pos);
}

function focusActiveStation() {
  if (!map || !naverMaps) return;
  const active = displayCandidates.value.find((candidate) => stationIdKey(candidate.station.station_id) === stationIdKey(activeStationId.value));
  if (active) {
    map.panTo(stationLatLng(active.station));
  }
}

function detectAuthFailure() {
  const canvasHtml = mapElement.value?.outerHTML || "";
  if (!canvasHtml.includes("auth_fail")) {
    return;
  }

  closeInfoWindow();
  markers.forEach((marker) => marker.setMap(null));
  markers = [];
  markerByStationId = new Map();
  if (userMarker) {
    userMarker.setMap(null);
    userMarker = null;
  }
  if (routeLine) {
    routeLine.setMap(null);
    routeLine = null;
  }
  map = null;
  mapState.value = "degraded";
  fallbackReason.value = "NAVER_MAPS_AUTH_FAILED";
}

function scheduleAuthFailureCheck() {
  window.clearTimeout(authFailureTimer);
  authFailureChecks = 0;
  const check = () => {
    authFailureChecks += 1;
    detectAuthFailure();
    if (mapState.value === "ready" && authFailureChecks < 10) {
      authFailureTimer = window.setTimeout(check, 1000);
    }
  };
  authFailureTimer = window.setTimeout(check, 1000);
}

async function initializeMap() {
  mapState.value = "loading";
  fallbackReason.value = "";

  try {
    await nextTick();
    naverMaps = await loadNaverMapsScript();

    // 초기 중심좌표 설정
    let centerCoords = new naverMaps.LatLng(37.5665, 126.9780); // 서울 시청 기본
    if (props.recommendation?.station) {
      centerCoords = stationLatLng(props.recommendation.station);
    } else if (hasUserLocation.value) {
      centerCoords = new naverMaps.LatLng(Number(props.userLocation.latitude), Number(props.userLocation.longitude));
    }

    map = new naverMaps.Map(mapElement.value, {
      center: centerCoords,
      zoom: 14,
      zoomControl: false, // 기본 줌 컨트롤 숨김 (커스텀 디자인 얹음)
      mapTypeControl: false
    });

    naverMaps.Event.addListener(map, "click", (event) => {
      const coord = event?.coord || event?.latlng;
      if (!coord || typeof coord.lat !== "function" || typeof coord.lng !== "function") {
        return;
      }
      emit("map-click", {
        latitude: Number(coord.lat().toFixed(6)),
        longitude: Number(coord.lng().toFixed(6)),
        source: "naver_map_click"
      });
    });

    renderMarkers();
    renderUserMarker();
    renderRouteLine();
    adjustMapBounds();
    lastBoundsKey = boundsKey();
    lastUserLocationKey = userLocationKey();
    mapState.value = "ready";
    scheduleAuthFailureCheck();
  } catch (error) {
    mapState.value = "degraded";
    fallbackReason.value = error.message || "NAVER_MAPS_LOAD_FAILED";
  }
}

watch(
  () => [
    props.recommendation,
    props.candidates,
    props.userLocation?.latitude,
    props.userLocation?.longitude
  ],
  () => {
    if (!props.recommendation && !hasUserLocation.value) return;
    if (!map) {
      initializeMap();
      return;
    }
    renderMarkers();
    renderUserMarker();
    renderRouteLine();
    const nextBoundsKey = boundsKey();
    const nextUserLocationKey = userLocationKey();
    if (displayCandidates.value.length && nextBoundsKey !== lastBoundsKey) {
      adjustMapBounds();
      lastBoundsKey = nextBoundsKey;
    } else if (nextUserLocationKey && nextUserLocationKey !== lastUserLocationKey) {
      focusOnUser();
      lastUserLocationKey = nextUserLocationKey;
    }
    lastUserLocationKey = nextUserLocationKey;
  },
  { immediate: true, deep: true }
);

watch(activeStationId, () => {
  renderMarkers();
  openInfoWindowForStation(activeStationId.value);
  renderRouteLine();
  focusActiveStation();
});

onBeforeUnmount(() => {
  window.clearTimeout(authFailureTimer);
  closeInfoWindow();
  markers.forEach((marker) => marker.setMap(null));
  markers = [];
  markerByStationId = new Map();
  if (userMarker) {
    userMarker.setMap(null);
    userMarker = null;
  }
  if (routeLine) {
    routeLine.setMap(null);
    routeLine = null;
  }
  map = null;
});
</script>

<template>
  <div class="fullScreenMap">
    <!-- 지도 로딩 실패 시 Fallback -->
    <div v-if="mapState === 'degraded'" class="mapFallback">
      <AlertTriangle :size="24" style="color: var(--accent);" />
      <div>
        <strong>지도를 불러올 수 없습니다</strong>
        <span>{{ fallbackReason }} (비장애 대체 추천 모드로 동작 중)</span>
      </div>
    </div>

    <!-- 지도 영역 -->
    <div v-show="mapState !== 'degraded'" ref="mapElement" class="mapCanvas" />


    <!-- 우측 상단 커스텀 줌 & 위치 퀵 컨트롤 -->
    <div v-if="mapState === 'ready'" class="mapControlPanel">
      <button class="mapControlBtn" type="button" @click="zoomIn" title="확대">
        <Plus :size="18" />
      </button>
      <button class="mapControlBtn" type="button" @click="zoomOut" title="축소">
        <Minus :size="18" />
      </button>
      <button
        class="mapControlBtn"
        type="button"
        :disabled="!hasUserLocation"
        @click="focusOnUser"
        title="현재 위치로 이동"
      >
        <LocateFixed :size="18" />
      </button>
    </div>

    <div v-if="mapState === 'ready' && routeFallbackReason" class="routeFallbackNotice">
      <AlertTriangle :size="14" />
      <span>{{ routeFallbackReason }}</span>
    </div>
  </div>
</template>

<style scoped src="./RecommendationMap.css"></style>
