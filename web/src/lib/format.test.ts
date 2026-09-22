import { describe, expect, it } from "vitest";
import { formatContext, formatCost, formatCount, formatText } from "./format";

describe("formatCost", () => {
  it("shows dollars with two decimals", () => {
    expect(formatCost(1.5)).toBe("$1.50");
    expect(formatCost(0)).toBe("$0.00");
  });

  it("shows -- for a missing cost", () => {
    expect(formatCost(null)).toBe("--");
    expect(formatCost(undefined)).toBe("--");
  });
});

describe("formatContext", () => {
  it("humanises a token count", () => {
    expect(formatContext(80_618)).toBe("81k");
  });

  it("shows -- for a missing context", () => {
    expect(formatContext(null)).toBe("--");
  });
});

describe("formatText", () => {
  it("shows -- for empty or blank text", () => {
    expect(formatText("")).toBe("--");
    expect(formatText("   ")).toBe("--");
    expect(formatText(null)).toBe("--");
  });

  it("passes real text through", () => {
    expect(formatText("hello")).toBe("hello");
  });
});

describe("formatCount", () => {
  it("shows -- for a missing count", () => {
    expect(formatCount(null)).toBe("--");
  });

  it("formats a present count", () => {
    expect(formatCount(1234)).toBe("1,234");
  });
});
