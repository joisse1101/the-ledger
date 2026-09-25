// Shared color plumbing for the grouped donut/bar charts (Overview's by project, a project's own
// by branch), so a group keeps the same hue in every one of them (see overview_stats.py's
// `group_totals` / `OTHER`).

/** Matches overview_stats.OTHER: the folded-tail row's group name. */
export const OTHER = "Other";

/** What a grouped chart's rows are; it words the headings, aria labels and tooltips. */
export type GroupLabel = "project" | "branch";

export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export const FONT_STACK = "system-ui, -apple-system, 'Segoe UI', sans-serif";

/** Reads the categorical/text/grid colors straight from tokens.css, so charts stay in sync
 *  with the theme without duplicating any hex values (mirrors TokensChart.tsx's themeColors). */
export function chartColors() {
  const style = getComputedStyle(document.documentElement);
  const read = (name: string) => style.getPropertyValue(name).trim();
  return {
    hues: Array.from({ length: 8 }, (_, i) => read(`--cat-${i}`)),
    muted: read("--muted-ink"),
    surface: read("--bg-surface"),
    text: read("--text-main"),
    text2: read("--text-muted"),
    grid: read("--border-subtle"),
  };
}

/** Domain/range for a `group` color encoding: `order` is the API's shared `group_order`
 *  (top-N by session count, "Other" last when present), so every chart on the page that uses
 *  this scale draws a given group in the same color, and "Other" always gets the muted ink. */
export function groupColorScale(
  order: string[],
  hues: string[],
  muted: string,
): { domain: string[]; range: string[] } {
  const hasOther = order.includes(OTHER);
  const namedCount = order.length - (hasOther ? 1 : 0);
  const range = hues.slice(0, namedCount);
  if (hasOther) range.push(muted);
  return { domain: order, range };
}

/** `group -> color`, from the same scale, for a legend drawn as plain HTML instead of
 *  inside a Vega-Lite spec (see GroupDonutChart: a chart-internal legend grid can't itself
 *  wrap long names without either clipping them or growing past its container). */
export function groupColorMap(order: string[], hues: string[], muted: string): Map<string, string> {
  const { domain, range } = groupColorScale(order, hues, muted);
  return new Map(domain.map((group, index) => [group, range[index]]));
}
