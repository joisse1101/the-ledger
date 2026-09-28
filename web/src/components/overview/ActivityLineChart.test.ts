import { describe, expect, it } from "vitest";
import { compile } from "vega-lite";
import type { ActivityBucket } from "../../api/types";
import { buildSpec } from "./ActivityLineChart";

const activity: ActivityBucket[] = [
  { minute: 540, label: "9:00am", sessions: 2, messages: 40 },
  { minute: 570, label: "9:30am", sessions: 5, messages: 90 },
  { minute: 600, label: "10:00am", sessions: 1, messages: 10 },
];

describe("ActivityLineChart spec", () => {
  it("draws one legend naming all three lines", () => {
    const { spec } = compile(buildSpec(activity, (n) => n) as never);
    const legends = (spec.legends ?? []) as { stroke?: string; title?: unknown }[];
    expect(legends).toHaveLength(1);
    const scale = (spec.scales ?? []).find((s) => s.name === legends[0].stroke) as { domain: unknown };
    expect(JSON.stringify(scale.domain)).toContain("Activity trend");
  });

  it("leaves the legend swatches at full strength so they match the lines", () => {
    // A layer's mark opacity leaks into the merged legend's symbols and dims every swatch.
    const { spec } = compile(buildSpec(activity, (n) => n) as never);
    const legends = (spec.legends ?? []) as { encode?: { symbols?: { update?: { opacity?: unknown } } } }[];
    const opacity = legends[0].encode?.symbols?.update?.opacity;
    expect(opacity === undefined || JSON.stringify(opacity) === '{"value":1}').toBe(true);
  });
});
