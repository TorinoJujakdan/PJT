import { computed, reactive, ref, watch } from "vue";
import { refreshNearbyStations } from "../api/stations";
import { recommendationStore } from "../stores/recommendationStore";
import { useSavedCards } from "./useSavedCards";
import { useStartLocation } from "./useStartLocation";
import { useVehicleProfiles } from "./useVehicleProfiles";

export function useSmartFuelDashboard({ isAuthenticated } = {}) {
  const fuel = reactive({
    fuel_type: "gasoline",
    target_amount: 50000,
    fuel_efficiency_kmpl: 12.5,
    travel_mode: "round_trip",
  });

  const tempCard = reactive({
    enabled: false,
    card_id: "manual-preview-card",
    card_name: "?? ?? ??",
    issuer_name: "????",
    discount_type: "per_liter",
    discount_value: 80,
    brand_scope: "all",
    min_payment_amount: null,
    max_discount_amount: 5000,
    monthly_remaining_discount: 12000,
    previous_month_spending: null,
    source_type: "manual",
    verification_status: "user_confirmed",
    card_image_url: null,
    source_url: null,
  });

  const priority = ref("optimal");
  const selectedStationId = ref(null);
  const showDetailCard = ref(false);
  const stationRefreshMessage = ref("");
  const refreshLoading = ref(false);
  const searchRadiusKm = ref(5);

  const response = computed(() => recommendationStore.response);
  const recommendation = computed(() => response.value?.recommendation || null);
  const rawCandidates = computed(() => response.value?.candidates || []);
  const candidates = computed(() => rawCandidates.value);
  const activeRecommendation = computed(() => {
    if (!response.value) return null;
    const mainRec = response.value.recommendation;
    if (!selectedStationId.value || mainRec?.station?.station_id === selectedStationId.value) {
      return mainRec;
    }
    return response.value.candidates?.find(
      (c) => c.station?.station_id === selectedStationId.value
    ) || mainRec;
  });

  function clearRecommendation() {
    recommendationStore.response = null;
    recommendationStore.error = null;
    selectedStationId.value = null;
    showDetailCard.value = false;
  }

  const {
    location,
    handleMapLocationSelect,
    handleMapClick,
  } = useStartLocation({ onStartLocationChanged: clearRecommendation });

  const {
    vehicles,
    selectedVehicleId,
    vehicle,
    isVehicleProfileApplied,
    loadVehicles,
    clearVehicles,
    resetSelectedVehicle,
  } = useVehicleProfiles({ fuel });

  const {
    cards,
    loadCards,
    clearCards,
    selectedCards,
  } = useSavedCards({ isAuthenticated, tempCard });

  watch(recommendation, (nextRecommendation) => {
    selectedStationId.value = nextRecommendation?.station?.station_id || null;
    showDetailCard.value = Boolean(nextRecommendation);
  });

  watch(selectedStationId, (id) => {
    if (id) {
      showDetailCard.value = true;
    }
  });

  function clearUserResources() {
    clearVehicles();
    clearCards();
  }

  function resetAfterLogout() {
    resetSelectedVehicle();
    clearRecommendation();
  }

  function handleCloseDetailCard() {
    showDetailCard.value = false;
    selectedStationId.value = null;
  }

  async function requestRecommendation() {
    if (!location.latitude || !location.longitude) {
      recommendationStore.error = {
        code: "MISSING_LOCATION",
        message: "?? ??? ?? ??? ???.",
      };
      return;
    }

    const request = {
      location: {
        latitude: location.latitude,
        longitude: location.longitude,
      },
      fuel_type: fuel.fuel_type,
      radius_km: searchRadiusKm.value,
      recommendation_priority: priority.value,
      target_amount: fuel.target_amount,
      travel_mode: fuel.travel_mode,
      cards: selectedCards(),
      include_candidates: true,
      vehicle: {
        fuel_efficiency_kmpl: fuel.fuel_efficiency_kmpl,
      },
    };

    refreshLoading.value = true;
    stationRefreshMessage.value = "?? ??? ???? ???? ????.";

    try {
      const refresh = await refreshNearbyStations({
        location: request.location,
        fuel_type: request.fuel_type,
        radius_km: Math.min(searchRadiusKm.value, 5),
      });

      const rows = refresh?.meta?.rows || 0;
      stationRefreshMessage.value =
        refresh.status === "ok"
          ? `?? ??? ${rows.toLocaleString("ko-KR")}?? ??????.`
          : "??? ?? ??? ???? ?????.";
    } catch (error) {
      stationRefreshMessage.value = "??? ?? ??? ??? ??? ?????.";
    }

    try {
      await recommendationStore.quote(request);
    } finally {
      refreshLoading.value = false;
    }
  }

  async function handleVehicleChanged() {
    await loadVehicles();
    if (recommendationStore.response && location.latitude && location.longitude) {
      await requestRecommendation();
      return;
    }
    clearRecommendation();
  }

  return {
    vehicles,
    cards,
    selectedVehicleId,
    location,
    fuel,
    tempCard,
    priority,
    selectedStationId,
    showDetailCard,
    stationRefreshMessage,
    refreshLoading,
    searchRadiusKm,
    vehicle,
    response,
    recommendation,
    rawCandidates,
    candidates,
    activeRecommendation,
    isVehicleProfileApplied,
    loadVehicles,
    loadCards,
    clearUserResources,
    resetAfterLogout,
    handleCloseDetailCard,
    requestRecommendation,
    handleVehicleChanged,
    handleMapLocationSelect,
    handleMapClick,
  };
}
