const API_URL_KEY = "mlopsforge_api_url";
const TOKEN_KEY = "mlopsforge_token";

// Deployed as a static build (e.g. Vercel), this frontend has no backend of
// its own to proxy through — unlike `npm run dev`'s Vite proxy, there's no
// server-side rewrite to lean on. The backend only exists on an HPC login
// node reached through a tunnel that gets started per-demo and whose URL
// changes each time, so baking a URL in at build time would mean a rebuild
// every time that tunnel restarts. Instead the API base URL is resolved at
// runtime: a `?api=` query param (for sharing a single working demo link)
// takes priority and is persisted + stripped from the URL, then localStorage
// (set via the sidebar's "API endpoint" control, for fixing it live mid-demo
// without re-sharing a link), then the build-time env var, then same-origin
// relative paths (correct when a backend really is colocated, e.g. `npm run
// dev`'s proxy or a full docker-compose deployment).
function resolveApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const params = new URLSearchParams(window.location.search);
    const fromQuery = params.get("api");
    if (fromQuery) {
      localStorage.setItem(API_URL_KEY, fromQuery);
      params.delete("api");
      const rest = params.toString();
      const cleanUrl = window.location.pathname + (rest ? `?${rest}` : "") + window.location.hash;
      window.history.replaceState(null, "", cleanUrl);
      return fromQuery;
    }
    const stored = localStorage.getItem(API_URL_KEY);
    if (stored) return stored;
  }
  return import.meta.env.VITE_API_URL ?? "/api/v1";
}

export function getApiBaseUrl(): string {
  return resolveApiBaseUrl();
}

// Setting a new API URL changes what every in-flight and future query hits —
// simplest correct thing is a full reload rather than trying to invalidate
// every TanStack Query cache entry by hand.
export function setApiBaseUrl(url: string): void {
  localStorage.setItem(API_URL_KEY, url.replace(/\/+$/, ""));
  window.location.reload();
}

const BASE_URL = resolveApiBaseUrl();

// Mirrors resolveApiBaseUrl() for WebSocket connections (api/ws.ts) — an
// absolute http(s) API URL (the deployed-frontend case, a tunnel on a
// different origin) becomes the equivalent ws(s) URL; a relative path (dev
// proxy / same-origin deployment) falls back to window.location.host, same
// as before.
export function getWsBaseUrl(): string {
  if (/^https?:\/\//.test(BASE_URL)) {
    return BASE_URL.replace(/^http/, "ws");
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${BASE_URL}`;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (res.status === 401) {
    // Token missing/expired/invalid — nothing this session does is valid
    // without a fresh login, so drop the stale token and send the user back.
    clearToken();
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
