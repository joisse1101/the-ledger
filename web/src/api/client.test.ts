import { afterEach, describe, expect, it, vi } from "vitest";
import { apiFetch, apiOrigin, ApiError, CSRF_HEADER, CSRF_VALUE, NetworkError, UnauthorizedError } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("apiFetch", () => {
  it("sends the CSRF header on a DELETE but not on a GET", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse(200, { ok: true })));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/sessions/abc", { method: "DELETE" });
    const deleteHeaders = fetchMock.mock.calls[0][1].headers as Headers;
    expect(deleteHeaders.get(CSRF_HEADER)).toBe(CSRF_VALUE);

    await apiFetch("/api/meta");
    const getHeaders = fetchMock.mock.calls[1][1].headers as Headers;
    expect(getHeaders.has(CSRF_HEADER)).toBe(false);
  });

  it("surfaces a 409's server message as an ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(409, { detail: "session is live and cannot be deleted" })),
    );

    await expect(apiFetch("/api/sessions/abc", { method: "DELETE" })).rejects.toMatchObject({
      status: 409,
      message: "session is live and cannot be deleted",
    } satisfies Partial<ApiError>);
  });

  it("turns a 401 into an UnauthorizedError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(401, {})));
    await expect(apiFetch("/api/live")).rejects.toBeInstanceOf(UnauthorizedError);
  });

  it("turns a dropped connection into a NetworkError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(apiFetch("/api/live")).rejects.toBeInstanceOf(NetworkError);
  });

  it("attaches the stored token as a Bearer header", async () => {
    localStorage.setItem("ledger_token", "abc123");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/live");
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer abc123");
  });

  it("sends no Authorization header once the stored token is cleared, and a 401 still surfaces", async () => {
    localStorage.setItem("ledger_token", "abc123");
    localStorage.clear();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(401, {}));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiFetch("/api/live")).rejects.toBeInstanceOf(UnauthorizedError);
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.has("Authorization")).toBe(false);
  });
});

describe("apiOrigin", () => {
  const location = { protocol: "http:", hostname: "192.168.1.20" };

  it("is relative in dev, where Vite's own proxy forwards /api to the backend", () => {
    expect(apiOrigin({ DEV: true, VITE_API_PORT: undefined }, location)).toBe("");
  });

  it("is the API's own origin, on the default port, once built", () => {
    expect(apiOrigin({ DEV: false, VITE_API_PORT: undefined }, location)).toBe("http://192.168.1.20:8501");
  });

  it("honours VITE_API_PORT when the API runs on a non-default port", () => {
    expect(apiOrigin({ DEV: false, VITE_API_PORT: "9000" }, location)).toBe("http://192.168.1.20:9000");
  });
});
