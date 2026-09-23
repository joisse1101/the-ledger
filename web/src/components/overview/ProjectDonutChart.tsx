import { useMemo, useRef } from "react";
import type { ProjectTotals } from "../../api/types";
import { useVegaEmbed } from "../../hooks/useVegaEmbed";
import { useTheme } from "../../theme/theme";
import { chartColors, FONT_STACK, projectColorMap, projectColorScale } from "./chartTheme";

function buildSpec(projects: ProjectTotals[], order: string[]) {
  const { hues, muted, surface, text, text2 } = chartColors();
  const { domain, range } = projectColorScale(order, hues, muted);
  const totalSessions = projects.reduce((sum, row) => sum + row.sessions, 0);

  return {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    background: null,
    width: 220,
    height: 220,
    view: { stroke: null },
    config: { font: FONT_STACK },
    layer: [
      {
        data: { values: projects },
        mark: { type: "arc", innerRadius: 62, outerRadius: 108, stroke: surface, strokeWidth: 2 },
        encoding: {
          theta: { field: "sessions", type: "quantitative" },
          order: { field: "sessions", sort: "descending" },
          // No `legend` here: the project key is drawn as plain HTML below instead (see
          // ProjectLegend), which wraps long project names cleanly at any container width
          // instead of a chart-internal legend grid clipping or overflowing its container.
          color: { field: "project", type: "nominal", scale: { domain, range }, legend: null },
          tooltip: [
            { field: "project", type: "nominal", title: "Project" },
            { field: "sessions", type: "quantitative", title: "Sessions" },
            { field: "share", type: "quantitative", title: "Share %", format: ".1f" },
          ],
        },
      },
      {
        data: { values: [{ label: totalSessions.toLocaleString() }] },
        mark: { type: "text", fontSize: 26, fontWeight: 600, color: text },
        encoding: { text: { field: "label", type: "nominal" } },
      },
      {
        data: { values: [{ label: "sessions" }] },
        mark: { type: "text", dy: 20, fontSize: 11, color: text2 },
        encoding: { text: { field: "label", type: "nominal" } },
      },
    ],
  };
}

function ProjectLegend({ projects, projectOrder }: ProjectDonutChartProps) {
  const { hues, muted } = chartColors();
  const colors = projectColorMap(projectOrder, hues, muted);
  return (
    <ul className="donut-legend">
      {projects.map((row) => (
        <li key={row.project} className="donut-legend-item" title={row.project}>
          <span className="donut-legend-dot" style={{ background: colors.get(row.project) }} />
          <span className="donut-legend-label">{row.project}</span>
        </li>
      ))}
    </ul>
  );
}

export interface ProjectDonutChartProps {
  projects: ProjectTotals[];
  projectOrder: string[];
}

/** Session counts by project as a donut. A fixed pixel size (rather than "container" width) because
 *  an arc mark's radius doesn't itself track a fluid width; the color key is a plain HTML list
 *  underneath (ProjectLegend) rather than a Vega-Lite legend, so long project names wrap instead
 *  of being clipped to a couple of characters in a cramped multi-column legend grid. */
export function ProjectDonutChart({ projects, projectOrder }: ProjectDonutChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  const spec = useMemo(
    () => buildSpec(projects, projectOrder),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- theme drives a rebuild for new colors
    [projects, projectOrder, theme],
  );
  useVegaEmbed(containerRef, spec);

  if (projects.length === 0) return null;

  return (
    <div className="donut-chart-wrap">
      <div ref={containerRef} className="donut-chart" role="img" aria-label="Sessions by project" />
      <ProjectLegend projects={projects} projectOrder={projectOrder} />
    </div>
  );
}
