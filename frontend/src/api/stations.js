import { apiRequest } from "./client";

const SEARCH_API_BASE_URL = import.meta.env.VITE_SEARCH_API_BASE_URL || "/search-api";

async function searchApiRequest(path) {
  const response = await fetch(`${SEARCH_API_BASE_URL}${path}`, {
    credentials: "include"
  });
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message = payload?.message || payload?.detail || "검색 API 요청을 처리하지 못했습니다.";
    const error = new Error(Array.isArray(message) ? "검색 API 요청을 처리하지 못했습니다." : message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

function withFastApiFallbackMeta(payload, error) {
  return {
    ...payload,
    meta: {
      ...(payload?.meta || {}),
      fastapi_search_status: "fallback_to_django",
      fastapi_search_error: error?.message || "FastAPI search API unavailable"
    }
  };
}

export async function searchLocations(query) {
  const encodedQuery = encodeURIComponent(query);
  try {
    return await searchApiRequest(`/locations/search/?query=${encodedQuery}`);
  } catch (error) {
    const djangoPayload = await apiRequest(`/stations/geocode/?query=${encodedQuery}`);
    return withFastApiFallbackMeta(djangoPayload, error);
  }
}

export function reverseGeocodeLocation(latitude, longitude) {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude)
  });
  return apiRequest(`/stations/reverse-geocode/?${params.toString()}`);
}

export function refreshNearbyStations(request) {
  return apiRequest("/stations/refresh/", {
    method: "POST",
    body: JSON.stringify(request)
  });
}
