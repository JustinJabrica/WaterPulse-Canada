/**
 * API client for WaterPulse frontend.
 *
 * Auth is handled via HTTPOnly cookies — the browser sends them
 * automatically with `withCredentials: true`.  We never touch
 * the JWT directly.
 *
 * A request interceptor reads the CSRF token from the `csrf_token`
 * cookie (which is NOT HTTPOnly) and attaches it as an
 * `X-CSRF-Token` header on every mutating request so the backend
 * can validate that the request came from our UI, not a third-party.
 */

import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Axios instance ──────────────────────────

const client = axios.create({
  baseURL: API_BASE,
  withCredentials: true, // always send cookies
  headers: { "Content-Type": "application/json" },
});

// ── CSRF helper ─────────────────────────────
// The backend sets a non-HTTPOnly cookie called `csrf_token`
// on login.  We read it here so we can echo it back as a header.

function getCSRFToken() {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

// ── Request interceptor ─────────────────────
// Attach CSRF token on any mutating method.

const MUTATING_METHODS = ["post", "put", "patch", "delete"];

client.interceptors.request.use((config) => {
  if (MUTATING_METHODS.includes(config.method)) {
    const csrf = getCSRFToken();
    if (csrf) {
      config.headers["X-CSRF-Token"] = csrf;
    }
  }
  return config;
});

// ── Response interceptor ────────────────────
// Unwrap `response.data` so callers get the payload directly,
// and normalize errors into a consistent shape.

client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const detail =
      error.response?.data?.detail || error.message || "Network error";
    const err = new Error(detail);
    err.status = error.response?.status;
    return Promise.reject(err);
  }
);

// ── Convenience methods ─────────────────────

const api = {
  get: (path, opts) => client.get(path, opts),
  post: (path, body, opts) => client.post(path, body, opts),
  put: (path, body, opts) => client.put(path, body, opts),
  patch: (path, body, opts) => client.patch(path, body, opts),
  del: (path, opts) => client.delete(path, opts),
};

export default api;
