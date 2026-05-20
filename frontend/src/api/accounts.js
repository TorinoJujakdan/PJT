import { apiRequest } from "./client";

export function getCurrentUser() {
  return apiRequest("/accounts/me/");
}

export function signupAccount(payload) {
  return apiRequest("/accounts/signup/", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function loginAccount(payload) {
  return apiRequest("/accounts/login/", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function logoutAccount() {
  return apiRequest("/accounts/logout/", {
    method: "POST"
  });
}

export function updateCurrentUser(payload) {
  return apiRequest("/accounts/me/", {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}
