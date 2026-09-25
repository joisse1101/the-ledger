import { useMemo, useRef } from "react";
import type { GroupTotals } from "../../api/types";
import { useVegaEmbed } from "../../hooks/useVegaEmbed";
import { useTheme } from "../../theme/theme";
import { useScaled } from "../../hooks/useScaled";
import type { Scaled } from "../../lib/uiScale";
import { capitalize, chartColors, FONT_STACK, groupColorMap, groupColorScale, type GroupLabel } from "./chartTheme";

function buildSpec(groups: GroupTotals[], order: string[], groupLabel: GroupLabel, scaled: Scaled) {
  const { hues, muted, surface, text, text2 } = chartColors();
  const { domain, range } = groupColorScale(order, hues, muted);
  const totalSessions = groups.reduce((sum, row) => sum + row.sessions, 0);

  return {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    background: null,
    width: scaled(220),
    height: scaled(220),
    view: { stroke: null },
    config: { font: FONT_STACK },
    layer: [
      {
        data: { values: groups },
        mark: { type: "arc", innerRadius: scaled(62), outerRadius: scaled(108), stroke: surface, strokeWidth: 2 },
        encoding: {
          theta: { field: "sessions", type: "quantitative" },
          order: { field: "sessions", sort: "descending" },
          // No `legend` here: the color key is drawn as plain HTML below instead (see
          // GroupLegend), which wraps long names cleanly at any container width
          // instead of a chart-internal legend grid clipping or overflowing its container.
          color: { field: "group", type: "nominal", scale: { domain, range }, legend: null },
          tooltip: [
            { field: "group", type: "nominal", title: capitalize(groupLabel) },
            { field: "sessions", type: "quantitative", title: "Sessions" },
            { field: "share", type: "quantitative", title: "Share %", format: ".1f" },
          ],
        },
      },
      {
        data: { values: [{ label: totalSessions.toLocaleString() }] },
        mark: { type: "text", fontSize: scaled(26), fontWeight: 600, color: text },
        encoding: { text: { field: "label", type: "nominal" } },
      },
      {
        data: { values: [{ label: "sessions" }] },
        mark: { type: "text", dy: scaled(20), fontSize: scaled(11), color: text2 },
        encoding: { text: { field: "label", type: "nominal" } },
      },
    ],
  };
}

function GroupLegend({ groups, groupOrder }: Pick<GroupDonutChartProps, "groups" | "groupOrder">) {
  const { hues, muted } = chartColors();
  const colors = groupColorMap(groupOrder, hues, muted);
  return (
    <ul className="donut-legend">
      {groups.map((row) => (
        <li key={row.group} className="donut-legend-item" title={row.group}>
          <span className="donut-legend-dot" style={{ background: colors.get(row.group) }} />
          <span className="donut-legend-label">{row.group}</span>
        </li>
      ))}
    </ul>
  );
}

export interface GroupDonutChartProps {
  groups: GroupTotals[];
  groupOrder: string[];
  /** What a row is: words the tooltip and aria label. */
  groupLabel: GroupLabel;
}

/** Session counts by group (a project, or a git branch) as a donut. A fixed pixel size (rather than
 *  "container" width) because an arc mark's radius doesn't itself track a fluid width; the color key
 *  is a plain HTML list underneath (GroupLegend) rather than a Vega-Lite legend, so long names wrap
 *  instead of being clipped to a couple of characters in a cramped multi-column legend grid. */
export function GroupDonutChart({ groups, groupOrder, groupLabel }: GroupDonutChartProps) {
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
    <div className="donut-chart-wrap">
      <div ref={containerRef} className="donut-chart" role="img" aria-label={`Sessions by ${groupLabel}`} />
      <GroupLegend groups={groups} groupOrder={groupOrder} />
    </div>
  );
}
