import { afterEach, describe, expect, it, vi } from "vitest";
import { apiFetch, ApiError, CSRF_HEADER, CSRF_VALUE, NetworkError, UnauthorizedError } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
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
});
