const viteEnv = import.meta.env || {};
const API_BASE_URL = viteEnv.VITE_API_BASE_URL || "/api/v1";
const CSRF_SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);

function getCookie(name) {
  if (typeof document === "undefined") return null;

  const cookies = document.cookie ? document.cookie.split("; ") : [];
  const prefix = `${name}=`;
  const match = cookies.find((cookie) => cookie.startsWith(prefix));
  return match ? decodeURIComponent(match.slice(prefix.length)) : null;
}

async function ensureCsrfToken() {
  let token = getCookie("csrftoken");
  if (token) return token;

  await fetch(`${API_BASE_URL}/accounts/me/`, {
    credentials: "include"
  });
  return getCookie("csrftoken");
}

export async function apiRequest(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (!CSRF_SAFE_METHODS.has(method) && !headers["X-CSRFToken"]) {
    const csrfToken = await ensureCsrfToken();
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const message = payload?.message || "요청을 처리하지 못했습니다.";
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}
