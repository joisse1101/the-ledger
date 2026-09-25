import { afterEach, describe, expect, it } from "vitest";
import { scaledBy, uiScale } from "./uiScale";

afterEach(() => {
  document.documentElement.style.fontSize = "";
});

describe("uiScale", () => {
  it("is 1 at the default 16px root", () => {
    document.documentElement.style.fontSize = "16px";
    expect(uiScale()).toBe(1);
  });

  it("follows a smaller root size", () => {
    document.documentElement.style.fontSize = "12.8px";
    expect(uiScale()).toBeCloseTo(0.8);
  });

  it("falls back to 1 when the root size can't be read", () => {
    document.documentElement.style.fontSize = "";
    expect(uiScale()).toBe(1);
  });
});

describe("scaledBy", () => {
  it("returns the size unchanged at a scale of 1", () => {
    expect(scaledBy(1)(260)).toBe(260);
  });

  it("shrinks with the scale and rounds to a tenth of a pixel", () => {
    const scaled = scaledBy(0.8);
    expect(scaled(260)).toBe(208);
    expect(scaled(11)).toBe(8.8);
    expect(scaled(9)).toBe(7.2);
  });
});
