import { computed, ref, watch } from "vue";
import { getMyVehicles } from "../api/vehicles";

export function useVehicleProfiles({ fuel }) {
  const vehicles = ref([]);
  const selectedVehicleId = ref("manual");
  const vehicle = computed(() => vehicles.value.find((v) => v.is_default) || vehicles.value[0] || null);
  const isVehicleProfileApplied = computed(() => selectedVehicleId.value !== "manual" && selectedVehicleId.value !== null);

  watch(
    () => vehicles.value,
    (list) => {
      if (list && list.length > 0) {
        const defaultVehicle = list.find((v) => v.is_default) || list[0];
        selectedVehicleId.value = defaultVehicle.id;
        fuel.fuel_type = defaultVehicle.fuel_type;
        fuel.fuel_efficiency_kmpl = Number(defaultVehicle.fuel_efficiency_kmpl);
      } else {
        selectedVehicleId.value = "manual";
      }
    },
    { immediate: true }
  );

  watch(selectedVehicleId, (id) => {
    if (id === "manual" || !vehicles.value) return;
    const found = vehicles.value.find((v) => v.id === id);
    if (found) {
      fuel.fuel_type = found.fuel_type;
      fuel.fuel_efficiency_kmpl = Number(found.fuel_efficiency_kmpl);
    }
  });

  async function loadVehicles() {
    try {
      const payload = await getMyVehicles();
      vehicles.value = payload.vehicles || [];
    } catch (error) {
      if (error.status !== 404) throw error;
      vehicles.value = [];
    }
  }

  function clearVehicles() {
    vehicles.value = [];
  }

  function resetSelectedVehicle() {
    selectedVehicleId.value = "manual";
  }

  return {
    vehicles,
    selectedVehicleId,
    vehicle,
    isVehicleProfileApplied,
    loadVehicles,
    clearVehicles,
    resetSelectedVehicle,
  };
}
