// One place that talks to the server. Every failure becomes an ApiError,
// UnauthorizedError or NetworkError so the UI can tell "sign in again" from
// "the server is away" from "the server said no".

import { getStoredToken } from "./token";

/** Sent on every state-changing request. A page on another site can't add a custom
 *  header without a CORS preflight (which the API only ever grants to its own
 *  frontend's origin — see design.md Decision 7), so this is what keeps a cross-site
 *  page from deleting anything. */
export const CSRF_HEADER = "X-Requested-With";
export const CSRF_VALUE = "ledger";

const DEFAULT_API_PORT = 8501;

/** Where API calls go. `npm run dev`'s Vite proxy (vite.config.ts) forwards relative
 *  `/api` paths to the backend, so dev keeps using those (import.meta.env.DEV is true
 *  there, and under Vitest). The built app is served by `vite preview` on its own
 *  origin (design.md Decision 2), so it has to call the API's own origin directly;
 *  VITE_API_PORT overrides the default port 8501 at build time. Params are injectable
 *  so this is testable without stubbing Vite's globals. */
export function apiOrigin(
  env: Pick<ImportMetaEnv, "DEV" | "VITE_API_PORT"> = import.meta.env,
  location: Pick<Location, "protocol" | "hostname"> = window.location,
): string {
  if (env.DEV) return "";
  const port = env.VITE_API_PORT || DEFAULT_API_PORT;
  return `${location.protocol}//${location.hostname}:${port}`;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** The server answered 401: this device has no valid token. */
export class UnauthorizedError extends ApiError {
  constructor() {
    super(401, "This device isn't signed in.");
    this.name = "UnauthorizedError";
  }
}

/** The server couldn't be reached at all (down, network dropped, wrong address). */
export class NetworkError extends Error {
  constructor() {
    super("Can't reach the server.");
    this.name = "NetworkError";
  }
}

async function errorMessage(response: Response): Promise<string> {
  const fallback = `${response.status} ${response.statusText}`.trim();
  try {
    const body = await response.json();
    // FastAPI puts its message in `detail`; a validation error makes it a list.
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail) && typeof body.detail[0]?.msg === "string") return body.detail[0].msg;
  } catch {
    // not JSON: fall through
  }
  return fallback || "The server reported an error.";
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (method !== "GET" && method !== "HEAD") headers.set(CSRF_HEADER, CSRF_VALUE);
  const token = getStoredToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(apiOrigin() + path, { ...init, method, headers });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new NetworkError();
  }

  if (response.status === 401) throw new UnauthorizedError();
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  return (await response.json()) as T;
}

export function withQuery(
  path: string,
  params: Record<string, string | number | string[] | undefined>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue;
    if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
    else search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `${path}?${text}` : path;
}
