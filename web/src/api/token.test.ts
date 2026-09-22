import { afterEach, describe, expect, it, vi } from "vitest";
import { consumeTokenFromUrl, getStoredToken } from "./token";

afterEach(() => {
  localStorage.clear();
});

describe("consumeTokenFromUrl", () => {
  it("stores a token found in the URL and strips it from the address", () => {
    const history = { replaceState: vi.fn() };
    consumeTokenFromUrl(
      { href: "http://localhost:4173/overview?token=abc123&x=1", pathname: "/overview", search: "?token=abc123&x=1", hash: "" },
      history,
    );

    expect(getStoredToken()).toBe("abc123");
    expect(history.replaceState).toHaveBeenCalledTimes(1);
    const [, , url] = history.replaceState.mock.calls[0];
    expect(url).toBe("/overview?x=1");
    expect(url).not.toContain("token");
  });

  it("keeps the path and hash when there is nothing left in the query", () => {
    const history = { replaceState: vi.fn() };
    consumeTokenFromUrl(
      { href: "http://192.168.1.20:4173/?token=abc#detail", pathname: "/", search: "?token=abc", hash: "#detail" },
      history,
    );

    expect(history.replaceState.mock.calls[0][2]).toBe("/#detail");
  });

  it("does nothing when the URL has no token", () => {
    const history = { replaceState: vi.fn() };
    consumeTokenFromUrl({ href: "http://localhost:4173/", pathname: "/", search: "", hash: "" }, history);

    expect(getStoredToken()).toBeNull();
    expect(history.replaceState).not.toHaveBeenCalled();
  });
});
