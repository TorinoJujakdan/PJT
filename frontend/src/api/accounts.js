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

export function checkUsernameAvailability(username) {
  return apiRequest(`/accounts/username-availability/?username=${encodeURIComponent(username)}`);
}

export async function signupAndAuthenticate(payload) {
  const signupPayload = await signupAccount(payload);

  // The signup endpoint should create a logged-in session, but verify it
  // before moving the user out of onboarding. If a browser/proxy drops the
  // session cookie, fall back to a normal login with the just-created account.
  const sessionPayload = await getCurrentUser().catch(() => null);
  if (sessionPayload?.authenticated && sessionPayload.user) {
    return { ...signupPayload, user: sessionPayload.user, authenticated: true };
  }

  const loginPayload = await loginAccount({
    username: payload.username,
    password: payload.password
  });
  return { ...loginPayload, authenticated: true };
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
