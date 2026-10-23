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

  it("keeps the branch wording for a branch chart", () => {
    const spec = buildSpec(groups, order, "branch", (n) => n) as unknown as BarSpec;
    expect(spec.encoding.y.title).toBe("% of top branch");
  });
});
