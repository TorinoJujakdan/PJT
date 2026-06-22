import { onMounted, reactive, watch } from "vue";
import { reverseGeocodeLocation } from "../api/stations";

const HOME_LOCATION_STORAGE_KEY = "smartfuel_home_location";

function isValidCoordinate(latitude, longitude) {
  const lat = Number(latitude);
  const lon = Number(longitude);
  return Number.isFinite(lat) && Number.isFinite(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
}

export function useStartLocation({ onStartLocationChanged } = {}) {
  const location = reactive({
    latitude: null,
    longitude: null,
    name: "",
    address: "",
    road_address: "",
    jibun_address: "",
    source: "unset",
    accuracy_m: null,
  });

  let hasLoadedPersistedLocation = false;
  let mapLocationRequestId = 0;

  function normalizeLocationPayload(payload) {
    if (!payload || !isValidCoordinate(payload.latitude, payload.longitude)) {
      return null;
    }

    return {
      latitude: Number(payload.latitude),
      longitude: Number(payload.longitude),
      name: payload.name || payload.address || "??? ???",
      address: payload.address || payload.road_address || payload.jibun_address || "",
      road_address: payload.road_address || "",
      jibun_address: payload.jibun_address || "",
      source: payload.source || "stored",
      accuracy_m: payload.accuracy_m ?? null,
      saved_at: payload.saved_at || new Date().toISOString(),
    };
  }

  function applyLocationPayload(payload) {
    const normalized = normalizeLocationPayload(payload);
    if (!normalized) return false;
    Object.assign(location, normalized);
    return true;
  }

  function applyStartLocationPayload(payload) {
    const applied = applyLocationPayload(payload);
    if (!applied) return false;
    onStartLocationChanged?.();
    return true;
  }

  function loadPersistedLocation() {
    try {
      const raw = window.localStorage.getItem(HOME_LOCATION_STORAGE_KEY);
      if (!raw) return false;
      return applyLocationPayload(JSON.parse(raw));
    } catch (error) {
      window.localStorage.removeItem(HOME_LOCATION_STORAGE_KEY);
      return false;
    }
  }

  function persistLocation() {
    const normalized = normalizeLocationPayload(location);
    if (!normalized) return;
    window.localStorage.setItem(
      HOME_LOCATION_STORAGE_KEY,
      JSON.stringify({
        ...normalized,
        saved_at: new Date().toISOString(),
      })
    );
  }

  function getBrowserPosition() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("GEOLOCATION_UNAVAILABLE"));
        return;
      }

      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 8000,
        maximumAge: 30000,
      });
    });
  }

  async function canUseStoredGeolocationPermission() {
    if (!navigator.permissions?.query) {
      return false;
    }

    try {
      const permission = await navigator.permissions.query({ name: "geolocation" });
      return permission.state === "granted";
    } catch (error) {
      return false;
    }
  }

  async function initializeBrowserLocationIfGranted() {
    if (!(await canUseStoredGeolocationPermission())) {
      return false;
    }

    try {
      const position = await getBrowserPosition();
      const latitude = Number(position.coords.latitude.toFixed(6));
      const longitude = Number(position.coords.longitude.toFixed(6));
      const payload = {
        latitude,
        longitude,
        name: "?? ??",
        address: "",
        source: "browser_geolocation",
        accuracy_m: position.coords.accuracy,
      };

      try {
        const response = await reverseGeocodeLocation(latitude, longitude);
        if (response.result) {
          Object.assign(payload, response.result, {
            source: "browser_geolocation",
            accuracy_m: position.coords.accuracy,
          });
        }
      } catch (error) {
        // ?????? ??? ??? ????? ????? ??? ????? ??.
      }

      return applyLocationPayload(payload);
    } catch (error) {
      return false;
    }
  }

  watch(
    () => [location.latitude, location.longitude, location.name, location.address, location.source, location.accuracy_m],
    () => {
      if (!hasLoadedPersistedLocation || !isValidCoordinate(location.latitude, location.longitude)) {
        return;
      }
      persistLocation();
    }
  );

  function handleMapLocationSelect(payload) {
    applyStartLocationPayload({
      ...payload,
      source: payload.source || "naver_map_search",
    });
  }

  async function handleMapClick(coords) {
    const latitude = Number(coords.latitude);
    const longitude = Number(coords.longitude);
    if (!isValidCoordinate(latitude, longitude)) return;

    const requestId = ++mapLocationRequestId;
    const payload = {
      latitude,
      longitude,
      name: "???? ??? ??",
      address: "",
      source: coords.source || "map_click",
      accuracy_m: null,
    };

    applyStartLocationPayload(payload);

    try {
      const response = await reverseGeocodeLocation(latitude, longitude);
      if (requestId !== mapLocationRequestId || !response.result) return;
      applyStartLocationPayload({
        ...payload,
        ...response.result,
        source: coords.source || "map_click",
        accuracy_m: null,
      });
    } catch (error) {
      // ?? ?? ?????? ??? ??? ????? ????? ??? ????? ??.
    }
  }

  onMounted(async () => {
    const restored = loadPersistedLocation();
    hasLoadedPersistedLocation = true;
    if (!restored) {
      await initializeBrowserLocationIfGranted();
    }
  });

  return {
    location,
    handleMapLocationSelect,
    handleMapClick,
  };
}
