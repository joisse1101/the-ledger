import { describe, expect, it } from "vitest";
import { compile } from "vega-lite";
import type { GroupTotals } from "../../api/types";
import { buildSpec } from "./GroupDonutChart";

const groups: GroupTotals[] = [
  { group: "main", sessions: 3, messages: 30, cost: 3, tokens: 1000, share: 75, messages_pct: 100, cost_pct: 100 },
  { group: "dev", sessions: 1, messages: 10, cost: 1, tokens: 3000, share: 25, messages_pct: 33.3, cost_pct: 33.3 },
];
const order = ["main", "dev"];

// buildSpec's layers have different encoding/data shapes (arc vs. center-label text), so TS infers
// `spec.layer` as a union rather than a tuple; these casts pick out the shape each test needs.
interface ArcLayer {
  encoding: { theta: { field: string } };
  data: { values: unknown[] };
}
interface TextLayer {
  data: { values: { label: string }[] };
}

describe("GroupDonutChart spec", () => {
  it("sizes the arcs by session count by default", () => {
    const spec = buildSpec(groups, order, "branch", "sessions", (n) => n);
    const arcLayer = spec.layer[0] as ArcLayer;
    expect(arcLayer.encoding.theta.field).toBe("sessions");
    // Sanity-check the spec still compiles.
    expect(() => compile(spec as never)).not.toThrow();
  });

  it("sizes the arcs by tokens, and shares them relative to the token total", () => {
    const spec = buildSpec(groups, order, "branch", "tokens", (n) => n);
    const arcLayer = spec.layer[0] as ArcLayer;
    expect(arcLayer.encoding.theta.field).toBe("tokens");
    const values = arcLayer.data.values as (GroupTotals & { _share: number })[];
    expect(values.find((row) => row.group === "main")!._share).toBeCloseTo(25); // 1000 / 4000
    expect(values.find((row) => row.group === "dev")!._share).toBeCloseTo(75); // 3000 / 4000
  });

  it("labels the center total in humanized token units", () => {
    const spec = buildSpec(groups, order, "branch", "tokens", (n) => n);
    const centerValueLayer = spec.layer[1] as TextLayer;
    expect(centerValueLayer.data.values[0].label).toBe("4k"); // 1000 + 3000
  });
});
