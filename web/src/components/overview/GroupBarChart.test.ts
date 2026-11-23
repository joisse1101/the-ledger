import { describe, expect, it } from "vitest";
import { compile } from "vega-lite";
import type { GroupTotals } from "../../api/types";
import { buildSpec } from "./GroupBarChart";

const groups: GroupTotals[] = [
  { group: "wt fix", sessions: 3, messages: 30, cost: 3, tokens: 1000, share: 75, messages_pct: 100, cost_pct: 100 },
  { group: "main", sessions: 1, messages: 10, cost: 1, tokens: 3000, share: 25, messages_pct: 33.3, cost_pct: 33.3 },
];
const order = ["wt fix", "main"];

interface BarSpec {
  encoding: { y: { title: string }; tooltip: { field: string; title: string }[] };
}

describe("GroupBarChart spec", () => {
  it("words the axis and tooltip for a worktree chart as branch / worktree", () => {
    const spec = buildSpec(groups, order, "worktree", (n) => n) as unknown as BarSpec;
    expect(spec.encoding.y.title).toBe("% of top branch / worktree");
    expect(spec.encoding.tooltip.find((entry) => entry.field === "group")?.title).toBe("Branch / worktree");
    expect(() => compile(buildSpec(groups, order, "worktree", (n) => n) as never)).not.toThrow();
  });

  it("plots the API's 0-100 percentages as-is on a 0-115 axis, so bars are visible", () => {
    // messages_pct / cost_pct are already percent (100 = the top group). A fraction (0.33) would
    // draw bars under a pixel tall on this axis, which is how a wrong mock once showed no bars.
    const spec = buildSpec(groups, order, "project", (n) => n) as unknown as {
      data: { values: { group: string; metric: string; pct: number }[] };
      encoding: { y: { scale: { domain: number[] } } };
    };
    expect(spec.encoding.y.scale.domain).toEqual([0, 115]);
    const top = spec.data.values.filter((v) => v.group === "wt fix");
    expect(top.map((v) => v.pct)).toEqual([100, 100]);
    expect(spec.data.values.find((v) => v.group === "main" && v.metric === "Cost")?.pct).toBe(33.3);
  });

  it("keeps the branch wording for a branch chart", () => {
    const spec = buildSpec(groups, order, "branch", (n) => n) as unknown as BarSpec;
    expect(spec.encoding.y.title).toBe("% of top branch");
  });
});
