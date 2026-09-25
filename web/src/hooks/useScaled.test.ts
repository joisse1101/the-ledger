import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useScaled } from "./useScaled";

afterEach(() => {
  document.documentElement.style.fontSize = "";
});

describe("useScaled", () => {
  it("scales by the current root font size", () => {
    document.documentElement.style.fontSize = "12.8px";
    const { result } = renderHook(() => useScaled());
    expect(result.current(260)).toBe(208);
  });

  it("returns a new scaler when the root size changes on resize, and keeps it otherwise", () => {
    document.documentElement.style.fontSize = "16px";
    const { result } = renderHook(() => useScaled());
    const before = result.current;
    expect(before(260)).toBe(260);

    act(() => window.dispatchEvent(new Event("resize")));
    expect(result.current).toBe(before);

    document.documentElement.style.fontSize = "12.8px";
    act(() => window.dispatchEvent(new Event("resize")));
    expect(result.current).not.toBe(before);
    expect(result.current(260)).toBe(208);
  });
});
