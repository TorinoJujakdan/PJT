import { apiRequest } from "./client";

export function getMyVehicle() {
  return apiRequest("/me/vehicle/");
}

export function saveMyVehicle(payload) {
  return apiRequest("/me/vehicle/", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getMyVehicles() {
  return apiRequest("/me/vehicles/");
}

export function addVehicle(payload) {
  return apiRequest("/me/vehicles/", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function deleteVehicle(id) {
  return apiRequest(`/me/vehicles/${id}/`, {
    method: "DELETE"
  });
}

export function updateVehicle(id, payload) {
  return apiRequest(`/me/vehicles/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function setDefaultVehicle(id) {
  return apiRequest(`/me/vehicles/${id}/set-default/`, {
    method: "POST"
  });
}
