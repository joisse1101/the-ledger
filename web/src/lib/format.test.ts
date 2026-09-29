import { describe, expect, it } from "vitest";
import {
  estimatedCostTooltip,
  formatContext,
  formatCost,
  formatCount,
  formatText,
  formatTimeLeft,
} from "./format";

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

describe("estimatedCostTooltip", () => {
  it("names a single unpriced model", () => {
    const tooltip = estimatedCostTooltip(["claude-opus-5-5"], false);
    expect(tooltip).toContain("this app doesn't yet recognize this model (claude-opus-5-5)");
    expect(tooltip).toContain("its turns aren't priced");
  });

  it("names several unpriced models, joined with 'and'", () => {
    const tooltip = estimatedCostTooltip(["claude-opus-5-5", "claude-haiku-4-5-20251001"], false);
    expect(tooltip).toContain(
      "these models (claude-opus-5-5 and claude-haiku-4-5-20251001)",
    );
    expect(tooltip).toContain("their turns aren't priced");
  });

  it("takes the named-model reason even when cost-state also flagged the session", () => {
    const tooltip = estimatedCostTooltip(["claude-opus-5-5"], true);
    expect(tooltip).toContain("claude-opus-5-5");
    expect(tooltip).not.toContain("Claude Code flagged");
  });

  it("falls back to the cost-state-flagged reason when no model was named", () => {
    const tooltip = estimatedCostTooltip([], true);
    expect(tooltip).toBe(
      "Estimate: the sum of this session's own priced messages. It excludes any subagent spend, and " +
        "Claude Code flagged part of this session's cost as unpriced in a way this app can't attribute " +
        "to a specific model, so the true total is higher than shown.",
    );
  });

  it("falls back to the generic no-report-yet reason when neither applies", () => {
    const tooltip = estimatedCostTooltip([], false);
    expect(tooltip).toBe(
      "Estimate: the sum of this session's own priced messages. It excludes any subagent spend, and " +
        "Claude Code hasn't reported a final cost for this session yet - it's either still running, or " +
        "from a build too old to report one - so this total may change.",
    );
  });
});

describe("formatTimeLeft", () => {
  it("shows hours and minutes, minutes alone, or under a minute", () => {
    expect(formatTimeLeft(8 * 3_600_000)).toBe("8h 0m");
    expect(formatTimeLeft(7 * 3_600_000 + 59 * 60_000 + 30_000)).toBe("7h 59m");
    expect(formatTimeLeft(45 * 60_000)).toBe("45m");
    expect(formatTimeLeft(59_000)).toBe("<1m");
  });

  it("treats zero, negative and non-finite as under a minute", () => {
    expect(formatTimeLeft(0)).toBe("<1m");
    expect(formatTimeLeft(-5000)).toBe("<1m");
    expect(formatTimeLeft(Number.NaN)).toBe("<1m");
  });
});
