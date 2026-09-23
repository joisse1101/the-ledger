import { useMemo, useRef } from "react";
import type { HourlyBucket } from "../../api/types";
import { useVegaEmbed } from "../../hooks/useVegaEmbed";
import { useTheme } from "../../theme/theme";
import { formatCount } from "../../lib/format";
import { chartColors, FONT_STACK } from "./chartTheme";

const METRICS = ["Sessions", "Messages"] as const;

interface Record_ {
  label: string;
  metric: (typeof METRICS)[number];
  pct: number;
  formatted: string;
}

function records(hourly: HourlyBucket[]): Record_[] {
  const rows: Record_[] = [];
  for (const bucket of hourly) {
    rows.push({ label: bucket.label, metric: "Sessions", pct: bucket.sessions_pct, formatted: formatCount(bucket.sessions) });
    rows.push({ label: bucket.label, metric: "Messages", pct: bucket.messages_pct, formatted: formatCount(bucket.messages) });
  }
  return rows;
}

function buildSpec(hourly: HourlyBucket[]) {
  const { hues, text2, grid } = chartColors();
  const hourOrder = hourly.map((bucket) => bucket.label);
  // "Messages" keeps the hue it has in the project chart above (color follows the measure,
  // not the chart it happens to be drawn in).
  const colors = [hues[1], hues[0]];

  return {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    background: null,
    width: "container",
    height: 260,
    view: { stroke: null },
    config: { font: FONT_STACK, legend: { labelColor: text2, labelFontSize: 12 } },
    data: { values: records(hourly) },
    mark: { type: "bar", cornerRadiusTopLeft: 3, cornerRadiusTopRight: 3 },
    encoding: {
      x: {
        field: "label",
        type: "nominal",
        sort: hourOrder,
        title: null,
        axis: {
          domain: false,
          ticks: false,
          labelAngle: 0,
          labelColor: text2,
          labelFontSize: 9,
          labelOverlap: "parity",
        },
      },
      xOffset: { field: "metric", sort: METRICS },
      y: {
        field: "pct",
        type: "quantitative",
        title: "% of busiest hour",
        axis: {
          domain: false,
          gridColor: grid,
          labelColor: text2,
          labelFontSize: 10,
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
        { field: "label", type: "nominal", title: "Hour" },
        { field: "metric", type: "nominal", title: "Metric" },
        { field: "formatted", type: "nominal", title: "Value" },
      ],
    },
  };
}

export interface HourlyBarChartProps {
  hourly: HourlyBucket[];
}

/** Sessions and messages by local hour of day, normalized the same way as the project chart
 *  above. The server already
 *  trims `hourly` to the contiguous range of hours that had any activity. */
export function HourlyBarChart({ hourly }: HourlyBarChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  const spec = useMemo(
    () => buildSpec(hourly),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- theme drives a rebuild for new colors
    [hourly, theme],
  );
  useVegaEmbed(containerRef, spec);

  if (hourly.length === 0) return null;

  return (
    <div className="overview-chart">
      <h2 className="chart-heading">Activity by Hour of Day</h2>
      <p className="chart-caption">
        Each metric is shown as a % of its own busiest hour (e.g. a Sessions bar at 50% means
        that hour had half as many sessions as the busiest hour for sessions) — Sessions and
        Messages are scaled independently.
      </p>
      <div ref={containerRef} className="bar-chart" role="img" aria-label="Activity by hour of day" />
    </div>
  );
}
