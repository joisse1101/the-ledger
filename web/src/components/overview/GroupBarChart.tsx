import { useMemo, useRef } from "react";
import type { GroupTotals } from "../../api/types";
import { useVegaEmbed } from "../../hooks/useVegaEmbed";
import { useTheme } from "../../theme/theme";
import { useScaled } from "../../hooks/useScaled";
import type { Scaled } from "../../lib/uiScale";
import { formatCost, formatCount } from "../../lib/format";
import { capitalize, chartColors, FONT_STACK, type GroupLabel } from "./chartTheme";

const METRICS = ["Messages", "Cost"] as const;

interface Record_ {
  group: string;
  metric: (typeof METRICS)[number];
  pct: number;
  formatted: string;
}

function records(groups: GroupTotals[]): Record_[] {
  const rows: Record_[] = [];
  for (const row of groups) {
    rows.push({ group: row.group, metric: "Messages", pct: row.messages_pct, formatted: formatCount(row.messages) });
    rows.push({ group: row.group, metric: "Cost", pct: row.cost_pct, formatted: formatCost(row.cost) });
  }
  return rows;
}

function buildSpec(groups: GroupTotals[], order: string[], groupLabel: GroupLabel, scaled: Scaled) {
  const { hues, text2, grid } = chartColors();
  // "Messages" stays on categorical slot 0 everywhere it appears on this page (also the hourly
  // chart below), so that measure's color is consistent across both charts.
  const colors = [hues[0], hues[1]];

  return {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    background: null,
    width: "container",
    height: scaled(280),
    view: { stroke: null },
    config: { font: FONT_STACK, legend: { labelColor: text2, labelFontSize: scaled(12) } },
    data: { values: records(groups) },
    // A per-bar value label has nowhere to go without
    // overlapping its neighbor once more than a couple of groups are on screen - the
    // axis plus the tooltip (which does carry the exact formatted value) cover that instead.
    mark: { type: "bar", cornerRadiusTopLeft: scaled(3), cornerRadiusTopRight: scaled(3) },
    encoding: {
      x: {
        field: "group",
        type: "nominal",
        sort: order,
        title: null,
        axis: {
          domain: false,
          ticks: false,
          labelColor: text2,
          labelFontSize: scaled(11),
          labelAngle: -25,
          labelLimit: scaled(110),
        },
      },
      xOffset: { field: "metric", sort: METRICS },
      y: {
        field: "pct",
        type: "quantitative",
        title: `% of top ${groupLabel}`,
        scale: { domain: [0, 115] },
        axis: {
          domain: false,
          gridColor: grid,
          labelColor: text2,
          labelFontSize: scaled(10),
          titleColor: text2,
          values: [0, 25, 50, 75, 100],
        },
      },
      color: {
        field: "metric",
        type: "nominal",
        scale: { domain: METRICS, range: colors },
        legend: { title: null, orient: "top" },
      },
      tooltip: [
        { field: "group", type: "nominal", title: capitalize(groupLabel) },
        { field: "metric", type: "nominal", title: "Metric" },
        { field: "formatted", type: "nominal", title: "Value" },
      ],
    },
  };
}

export interface GroupBarChartProps {
  groups: GroupTotals[];
  groupOrder: string[];
  /** What a row is: words the heading, caption, aria label and tooltip. */
  groupLabel: GroupLabel;
}

/** Messages and cost per group (a project, or a git branch) as grouped bars, each normalized to %
 *  of its own top group so the two independently-scaled measures can share one axis instead of a
 *  dual-axis chart. */
export function GroupBarChart({ groups, groupOrder, groupLabel }: GroupBarChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  const scaled = useScaled();
  const spec = useMemo(
    () => buildSpec(groups, groupOrder, groupLabel, scaled),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- theme drives a rebuild for new colors
    [groups, groupOrder, groupLabel, theme, scaled],
  );
  useVegaEmbed(containerRef, spec);

  if (groups.length === 0) return null;

  return (
    <div className="overview-chart">
      <h2 className="chart-heading">Messages &amp; Cost by {capitalize(groupLabel)}</h2>
      <p className="chart-caption">
        Each metric is shown as a % of its own top {groupLabel} (e.g. a Cost bar at 50% means that{" "}
        {groupLabel} cost half as much as the priciest {groupLabel}) — Messages and Cost are scaled
        independently.
      </p>
      <div ref={containerRef} className="bar-chart" role="img" aria-label={`Messages and cost by ${groupLabel}`} />
    </div>
  );
}
