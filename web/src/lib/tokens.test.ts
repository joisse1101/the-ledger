import { describe, expect, it } from "vitest";
import { formatGrowth, humanizeTokens } from "./tokens";

describe("humanizeTokens", () => {
  it("keeps small counts exact", () => {
    expect(humanizeTokens(0)).toBe("0");
    expect(humanizeTokens(742)).toBe("742");
  });

  it("rounds to the nearest thousand with a k suffix", () => {
    expect(humanizeTokens(80_618)).toBe("81k");
  });

  it("uses one decimal with an M suffix at a million and above", () => {
    expect(humanizeTokens(1_234_567)).toBe("1.2M");
  });
});

describe("formatGrowth", () => {
  it("marks growth with an up arrow and a plus sign", () => {
    expect(formatGrowth(2100)).toBe("▲ +2.1k");
  });

  it("marks shrinkage with a down arrow and a minus sign", () => {
    expect(formatGrowth(-500)).toBe("▼ -500");
  });

  it("marks no change with a dot", () => {
    expect(formatGrowth(0)).toBe("• 0");
  });
});
