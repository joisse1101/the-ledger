import { useMemo, useRef } from "react";
import type { ProjectTotals } from "../../api/types";
import { useVegaEmbed } from "../../hooks/useVegaEmbed";
import { useTheme } from "../../theme/theme";
import { useScaled } from "../../hooks/useScaled";
import type { Scaled } from "../../lib/uiScale";
import { formatCost, formatCount } from "../../lib/format";
import { chartColors, FONT_STACK } from "./chartTheme";

const METRICS = ["Messages", "Cost"] as const;

interface Record_ {
  project: string;
  metric: (typeof METRICS)[number];
  pct: number;
  formatted: string;
}

function records(projects: ProjectTotals[]): Record_[] {
  const rows: Record_[] = [];
  for (const row of projects) {
    rows.push({ project: row.project, metric: "Messages", pct: row.messages_pct, formatted: formatCount(row.messages) });
    rows.push({ project: row.project, metric: "Cost", pct: row.cost_pct, formatted: formatCost(row.cost) });
  }
  return rows;
}

function buildSpec(projects: ProjectTotals[], order: string[], scaled: Scaled) {
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
    data: { values: records(projects) },
    // A per-bar value label has nowhere to go without
    // overlapping its neighbor once more than a couple of project groups are on screen - the
    // axis plus the tooltip (which does carry the exact formatted value) cover that instead.
    mark: { type: "bar", cornerRadiusTopLeft: scaled(3), cornerRadiusTopRight: scaled(3) },
    encoding: {
      x: {
        field: "project",
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
        title: "% of top project",
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
        { field: "project", type: "nominal", title: "Project" },
        { field: "metric", type: "nominal", title: "Metric" },
        { field: "formatted", type: "nominal", title: "Value" },
      ],
    },
  };
}

export interface ProjectBarChartProps {
  projects: ProjectTotals[];
  projectOrder: string[];
}

/** Messages and cost per project as grouped bars, each normalized to % of its own top project so
 *  the two independently-scaled measures can share one axis instead of a dual-axis chart. */
export function ProjectBarChart({ projects, projectOrder }: ProjectBarChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  const scaled = useScaled();
  const spec = useMemo(
    () => buildSpec(projects, projectOrder, scaled),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- theme drives a rebuild for new colors
    [projects, projectOrder, theme, scaled],
  );
  useVegaEmbed(containerRef, spec);

  if (projects.length === 0) return null;

  return (
    <div className="overview-chart">
      <h2 className="chart-heading">Messages &amp; Cost by Project</h2>
      <p className="chart-caption">
        Each metric is shown as a % of its own top project (e.g. a Cost bar at 50% means that
        project cost half as much as the priciest project) — Messages and Cost are scaled
        independently.
      </p>
      <div ref={containerRef} className="bar-chart" role="img" aria-label="Messages and cost by project" />
    </div>
  );
}
