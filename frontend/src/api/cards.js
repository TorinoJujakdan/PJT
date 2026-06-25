import { apiRequest } from "./client.js";

export function getMyCards() {
  return apiRequest("/me/cards/");
}

export function createMyCard(payload) {
  return apiRequest("/me/cards/", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function createMyCardFromCatalog(payload) {
  return apiRequest("/me/cards/from-catalog/", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateMyCard(cardId, payload) {
  return apiRequest(`/me/cards/${cardId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function deleteMyCard(cardId) {
  return apiRequest(`/me/cards/${cardId}/`, {
    method: "DELETE"
  });
}

export function searchCardCatalog(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      query.set(key, value);
    }
  });
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest(`/cards/catalog/${suffix}`);
}
