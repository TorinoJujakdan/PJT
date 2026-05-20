<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { AlertTriangle, MapPinned } from "@lucide/vue";
import { loadNaverMapsScript } from "../utils/naverMapLoader";

const props = defineProps({
  recommendation: {
    type: Object,
    required: true
  },
  candidates: {
    type: Array,
    default: () => []
  },
  selectedStationId: {
    type: [Number, String],
    default: null
  }
});

const emit = defineEmits(["select"]);

const mapElement = ref(null);
const mapState = ref("idle");
const fallbackReason = ref("");

let map = null;
let naverMaps = null;
let markers = [];
let authFailureTimer = null;
let authFailureChecks = 0;

const displayCandidates = computed(() => {
  const seen = new Set();
  return [props.recommendation, ...props.candidates].filter((candidate) => {
    const station = candidate?.station;
    if (!station?.station_id || seen.has(station.station_id)) {
      return false;
    }
    seen.add(station.station_id);
    return Number.isFinite(Number(station.latitude)) && Number.isFinite(Number(station.longitude));
  });
});

const activeStationId = computed(() => props.selectedStationId || props.recommendation.station.station_id);

function markerIcon(candidate, isRecommended, isActive) {
  const station = candidate.station;
  const color = isRecommended ? "var(--primary)" : "var(--slate-600)";
  const label = isRecommended ? "★ 최적추천" : station.brand;
  const price = `${Number(station.fuel_price_per_liter).toLocaleString("ko-KR")}원`;

  return {
    content: `<button class="mapMarker${isRecommended ? " recommended" : ""}${isActive ? " active" : ""}" type="button" aria-label="Select station" style="--marker-color:${color};">
                <div style="font-size: 9px; font-weight: 800; opacity: 0.9; text-transform: uppercase;">${label}</div>
                <div style="font-size: 12px; font-weight: 900; margin-top: 1px; color: var(--secondary);">${price}</div>
              </button>`,
    anchor: new naverMaps.Point(45, 20)
  };
}

function stationLatLng(station) {
  return new naverMaps.LatLng(Number(station.latitude), Number(station.longitude));
}

function renderMarkers() {
  if (!map || !naverMaps) return;

  markers.forEach((marker) => marker.setMap(null));
  markers = displayCandidates.value.map((candidate) => {
    const station = candidate.station;
    const isRecommended = station.station_id === props.recommendation.station.station_id;
    const isActive = station.station_id === activeStationId.value;
    const marker = new naverMaps.Marker({
      position: stationLatLng(station),
      map,
      title: station.name,
      icon: markerIcon(candidate, isRecommended, isActive),
      zIndex: isActive ? 20 : isRecommended ? 10 : 1
    });

    naverMaps.Event.addListener(marker, "click", () => {
      emit("select", station.station_id);
    });

    return marker;
  });
}

function focusActiveStation() {
  if (!map || !naverMaps) return;
  const active = displayCandidates.value.find((candidate) => candidate.station.station_id === activeStationId.value);
  if (active) {
    map.panTo(stationLatLng(active.station));
  }
}

function detectAuthFailure() {
  const canvasHtml = mapElement.value?.outerHTML || "";
  if (!canvasHtml.includes("auth_fail")) {
    return;
  }

  markers.forEach((marker) => marker.setMap(null));
  markers = [];
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
    const centerStation = props.recommendation.station;
    map = new naverMaps.Map(mapElement.value, {
      center: stationLatLng(centerStation),
      zoom: 14
    });
    renderMarkers();
    focusActiveStation();
    mapState.value = "ready";
    scheduleAuthFailureCheck();
  } catch (error) {
    mapState.value = "degraded";
    fallbackReason.value = error.message || "NAVER_MAPS_LOAD_FAILED";
  }
}

watch(
  () => [props.recommendation, props.candidates],
  () => {
    if (!props.recommendation) return;
    if (!map) {
      initializeMap();
      return;
    }
    renderMarkers();
    focusActiveStation();
  },
  { immediate: true }
);

watch(activeStationId, () => {
  renderMarkers();
  focusActiveStation();
});

onBeforeUnmount(() => {
  window.clearTimeout(authFailureTimer);
  markers.forEach((marker) => marker.setMap(null));
  markers = [];
  map = null;
});
</script>

<template>
  <section class="panel mapPanel">
    <div class="panelHeader">
      <div>
        <p class="eyebrow">Map</p>
        <h2>Station locations</h2>
      </div>
      <MapPinned :size="22" />
    </div>

    <div v-if="mapState === 'degraded'" class="mapFallback">
      <AlertTriangle :size="22" />
      <div>
        <strong>Map unavailable</strong>
        <span>{{ fallbackReason }}</span>
      </div>
    </div>
    <div v-show="mapState !== 'degraded'" ref="mapElement" class="mapCanvas" />

    <div class="mapLegend">
      <span><i class="legendDot recommendedDot"></i>Recommended</span>
      <span><i class="legendDot candidateDot"></i>Candidate</span>
    </div>
  </section>
</template>
