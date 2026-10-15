import { describe, expect, it } from "vitest";
import type { ContextBreakdown } from "../api/types";
import { REMAINDER_NAME, formatShare, responseRows, tooltipContent } from "./contextBreakdown";

const breakdown: ContextBreakdown = {
  snapshots: [
    { position: 0, categories: [] },
    {
      position: 1,
      categories: [
        { name: "Skills", tokens: 6_700, items: [{ label: "review", tokens: 4_000 }, { label: "deploy", tokens: 2_700 }] },
        { name: "Memory files", tokens: 1_000, items: [{ label: "proj/CLAUDE.md", tokens: 1_000 }] },
      ],
    },
  ],
  turns: [
    { snapshot: 0, growth: [], remainder: 10_000 },
    { snapshot: 1, growth: [{ tool: "Read", tokens: 5_000 }, { tool: "Bash", tokens: -200 }], remainder: 15_800 },
  ],
};

describe("formatShare", () => {
  it("is the share of the response's own context", () => {
    expect(formatShare(6_700, 28_300)).toBe("24%");
  });

  it("rounds to a whole percent", () => {
    expect(formatShare(1, 3)).toBe("33%");
    expect(formatShare(2, 3)).toBe("67%");
  });

  it("shows a positive share under half a percent as <1%", () => {
    expect(formatShare(10, 28_300)).toBe("<1%");
    expect(formatShare(0, 28_300)).toBe("0%");
  });

  it("is 0% for a zero context rather than dividing by it", () => {
    expect(formatShare(5, 0)).toBe("0%");
  });
});

describe("responseRows", () => {
  it("lists every row largest first and they sum to the response's context", () => {
    const rows = responseRows(breakdown, 1);

    expect(rows.map((r) => r.name)).toEqual([REMAINDER_NAME, "Skills", "Read", "Memory files", "Bash"]);
    expect(rows.reduce((sum, r) => sum + r.tokens, 0)).toBe(28_300);
  });

  it("marks only startup categories as estimates", () => {
    const rows = responseRows(breakdown, 1);

    expect(rows.filter((r) => r.estimated).map((r) => r.name)).toEqual(["Skills", "Memory files"]);
  });

  it("keeps a category's items and describes the remainder", () => {
    const rows = responseRows(breakdown, 1);

    expect(rows.find((r) => r.name === "Skills")?.items).toHaveLength(2);
    expect(rows.find((r) => r.name === REMAINDER_NAME)?.note).toMatch(/system prompt/i);
  });

  it("is empty for a response the breakdown does not cover", () => {
    expect(responseRows(breakdown, 7)).toEqual([]);
  });
});

describe("tooltipContent", () => {
  it("shows the context size and the largest categories with tokens and share", () => {
    const content = tooltipContent(responseRows(breakdown, 1), 2, 28_300);

    expect(content.title).toBe("Response 2: 28,300 tokens");
    expect(content.lines[0]).toEqual({ name: REMAINDER_NAME, value: "15,800 (56%)" });
    expect(content.lines[1]).toEqual({ name: "Skills", value: "~6,700 (24%)" });
    expect(content.estimateNote).not.toBeNull();
  });

  it("lists at most five categories and no items", () => {
    const rows = responseRows(breakdown, 1);
    const content = tooltipContent([...rows, ...rows], 2, 28_300);

    expect(content.lines).toHaveLength(5);
  });

  it("has no estimate note when only exact rows are listed", () => {
    const content = tooltipContent(responseRows(breakdown, 0), 1, 10_000);

    expect(content.lines).toEqual([{ name: REMAINDER_NAME, value: "10,000 (100%)" }]);
    expect(content.estimateNote).toBeNull();
  });
});
