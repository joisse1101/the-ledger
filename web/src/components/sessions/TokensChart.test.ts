import { describe, expect, it } from "vitest";
import { View, parse } from "vega";
import { compile } from "vega-lite";
import type { Turn } from "../../api/types";
import type { TooltipContent } from "../../lib/contextBreakdown";
import { breakdownTooltipHtml, buildSpec, mountTooltipIn } from "./TokensChart";

const escape = (value: string) => value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const content: TooltipContent = {
  title: "Response 2: 28,300 tokens",
  lines: [
    { name: "Everything else", value: "15,800 (56%)" },
    { name: "Skills", value: "~6,700 (24%)" },
  ],
  estimateNote: "~ estimated from the transcript",
};

describe("breakdownTooltipHtml", () => {
  it("lists the title, each category with its figure, and the estimate note", () => {
    const html = breakdownTooltipHtml(content, escape);

    expect(html).toContain("<h2>Response 2: 28,300 tokens</h2>");
    expect(html).toContain("Skills:</td><td class=\"value\">~6,700 (24%)</td>");
    expect(html).toContain("~ estimated from the transcript");
  });

  it("omits the estimate note when there is none", () => {
    expect(breakdownTooltipHtml({ ...content, estimateNote: null }, escape)).not.toContain("estimated");
  });

  it("escapes names that come from the transcript", () => {
    const html = breakdownTooltipHtml({ ...content, lines: [{ name: "<img src=x onerror=alert(1)>", value: "1 (1%)" }] }, escape);

    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;img");
  });
});

const turn = (context: number): Turn => ({
  message_id: `m${context}`,
  timestamp: null,
  new: 0,
  cache_read: context,
  cache_written: 0,
  output: 1,
  context,
  tools: [],
  cache_miss: false,
});

async function barOpacities(selected: number | null, change?: number | null) {
  const spec = buildSpec([turn(100), turn(200), turn(300)], [], (n) => n, true, selected);
  const view = new View(parse(compile(spec as never).spec), { renderer: "none" });
  await view.runAsync();
  if (change !== undefined) await view.signal("selectedResponse", change).runAsync();

  const opacities = new Map<number, number>();
  const visit = (node: { items?: unknown[]; marktype?: string }) => {
    for (const item of (node.items ?? []) as { datum?: { Response?: number }; opacity?: number; items?: unknown[]; marktype?: string }[]) {
      if (node.marktype === "rect" && item.datum?.Response !== undefined) opacities.set(item.datum.Response, item.opacity ?? 1);
      visit(item);
    }
  };
  visit((view.scenegraph() as unknown as { root: Parameters<typeof visit>[0] }).root);
  view.finalize();
  return [1, 2, 3].map((response) => opacities.get(response));
}

describe("selected bar highlight", () => {
  it("shows every bar at full strength when nothing is selected", async () => {
    expect(await barOpacities(null)).toEqual([1, 1, 1]);
  });

  it("dims every bar but the selected one", async () => {
    expect(await barOpacities(2)).toEqual([0.4, 1, 0.4]);
  });

  it("follows a selection made after the chart was embedded, without rebuilding the spec", async () => {
    expect(await barOpacities(null, 3)).toEqual([0.4, 0.4, 1]);
    expect(await barOpacities(3, null)).toEqual([1, 1, 1]);
  });

  it("does not let the bar opacity leak into the legend swatches", () => {
    const { spec } = compile(buildSpec([turn(100)], [], (n) => n, true, 1) as never);
    const legends = (spec.legends ?? []) as { encode?: { symbols?: { update?: { opacity?: unknown } } } }[];

    expect(JSON.stringify(legends.map((l) => l.encode?.symbols?.update?.opacity ?? null))).not.toContain("selectedResponse");
  });
});

describe("hit zones", () => {
  async function zones(count: number, plotWidth: number) {
    const turns = Array.from({ length: count }, (_, i) => turn(100 + i));
    const view = new View(parse(compile(buildSpec(turns, [], (n) => n, true, null) as never).spec), { renderer: "none" });
    view.signal("width", plotWidth);
    await view.runAsync();
    const found: { x: number; width: number; strokeWidth: number; response: number }[] = [];
    const visit = (node: { items?: unknown[]; marktype?: string }) => {
      for (const item of (node.items ?? []) as Record<string, any>[]) {
        if (node.marktype === "rect" && item.stroke === "transparent") {
          found.push({ x: item.x, width: item.width, strokeWidth: item.strokeWidth, response: item.datum.Response });
        }
        visit(item as never);
      }
    };
    visit((view.scenegraph() as unknown as { root: Parameters<typeof visit>[0] }).root);
    const width = view.signal("width") as number;
    view.finalize();
    return Object.assign(found.sort((a, b) => a.response - b.response), { width });
  }

  it("gives every response a zone, however many there are", async () => {
    expect((await zones(486, 700)).map((z) => z.response)).toEqual(Array.from({ length: 486 }, (_, i) => i + 1));
  });

  it("widens a pixel-wide bar to a full step, so zones tile the plot", async () => {
    const found = await zones(486, 700);
    const step = found[1].x - found[0].x;

    expect(found.width).toBeGreaterThan(0);
    expect(step).toBeCloseTo(found.width / 486, 1);
    for (const zone of found) expect(zone.width + zone.strokeWidth).toBeCloseTo(step, 1);
  });

  it("does not widen a zone beyond its step when there are only a few responses", async () => {
    const found = await zones(3, 700);
    const step = found[1].x - found[0].x;

    for (const zone of found) expect(zone.width + zone.strokeWidth).toBeCloseTo(step, 1);
  });
});

describe("mountTooltipIn", () => {
  it("moves vega-tooltip's element into the dialog so it shows above the modal", () => {
    const tooltip = document.createElement("div");
    tooltip.id = "vg-tooltip-element";
    document.body.appendChild(tooltip);
    const dialog = document.createElement("dialog");
    document.body.appendChild(dialog);

    mountTooltipIn(dialog);

    expect(tooltip.parentElement).toBe(dialog);
    tooltip.remove();
    dialog.remove();
  });

  it("leaves the tooltip alone when the chart is not inside a dialog", () => {
    const tooltip = document.createElement("div");
    tooltip.id = "vg-tooltip-element";
    document.body.appendChild(tooltip);

    mountTooltipIn(null);

    expect(tooltip.parentElement).toBe(document.body);
    tooltip.remove();
  });
});
