import { useMemo, useRef } from "react";
import type { ActivityBucket } from "../../api/types";
import { useVegaEmbed } from "../../hooks/useVegaEmbed";
import { useTheme } from "../../theme/theme";
import { useScaled } from "../../hooks/useScaled";
import type { Scaled } from "../../lib/uiScale";
import { activityTrend } from "../../lib/activityTrend";
import { chartColors, FONT_STACK } from "./chartTheme";

/** X-axis extent in minutes after midnight, widened when everything falls in one block. */
function xDomain(activity: ActivityBucket[]): [number, number] {
  const first = activity[0].minute;
  const last = activity[activity.length - 1].minute;
  return first === last ? [first - 60, last + 60] : [first, last];
}

/** Tick positions: every whole hour, or every 30 minutes when the span is under 3 hours (so a
 *  short span still gets labels). */
function axisTicks([first, last]: [number, number]): number[] {
  const step = last - first < 180 ? 30 : 60;
  const ticks: number[] = [];
  for (let minute = Math.ceil(first / step) * step; minute <= last; minute += step) ticks.push(minute);
  return ticks;
}

const MEASURES = ["Sessions", "Messages", "Activity trend"];

function withTrend(activity: ActivityBucket[]) {
  const trend = activityTrend(activity);
  return activity.map((bucket, i) => ({ ...bucket, trend: trend[i] }));
}

export function buildSpec(activity: ActivityBucket[], scaled: Scaled) {
  const { hues, text2, grid } = chartColors();
  const domain = xDomain(activity);
  // "Messages" keeps the hue it has in the project chart above (color follows the measure,
  // not the chart it happens to be drawn in).
  const sessionsColor = hues[1];
  const messagesColor = hues[0];

  // Every layer names its line with a constant, and all three carry this same scale and legend
  // so they merge into one shared legend. (One layer saying `legend: null` would disable it for
  // all of them.)
  const lineColor = (name: string) => ({
    datum: name,
    type: "nominal",
    scale: { domain: MEASURES, range: [sessionsColor, messagesColor, text2] },
    legend: { title: null, orient: "top", labelColor: text2, labelFontSize: scaled(12) },
  });

  const axisBase = {
    domain: false,
    labelColor: text2,
    labelFontSize: scaled(10),
    ticks: false,
    titleFontSize: scaled(11),
    titleFontWeight: "bold",
  };

  // One layer per measure so each gets its own y scale: Sessions on the left, Messages on the
  // right. Only the left axis draws gridlines, since the two scales' ticks don't line up.
  const measureLayer = (field: "sessions" | "messages", title: string, color: string, orient: "left" | "right") => ({
    mark: { type: "line", interpolate: "monotone", strokeWidth: scaled(2), point: { filled: true, size: scaled(24) } },
    encoding: {
      color: lineColor(title),
      y: {
        field,
        type: "quantitative",
        title,
        scale: { zero: true, nice: true },
        axis: {
          ...axisBase,
          orient,
          grid: orient === "left",
          gridColor: grid,
          titleColor: color,
          tickMinStep: 1,
        },
      },
      tooltip: [
        { field: "label", type: "nominal", title: "Time" },
        { field: "sessions", type: "quantitative", title: "Sessions", format: "," },
        { field: "messages", type: "quantitative", title: "Messages", format: "," },
        { field: "trend", type: "quantitative", title: "Activity trend", format: ".0f" },
      ],
    },
  });

  // The trend is its own 0-100 scale with no axis of its own (the two measure axes already
  // take both sides); its value is in the tooltip. Drawn first so the measure lines sit on top.
  // No `opacity` here: a mark's opacity is copied onto every swatch of the merged legend, which
  // washed out the Sessions and Messages swatches so they no longer matched their lines.
  const trendLayer = {
    mark: { type: "line", interpolate: "monotone", strokeWidth: scaled(2) },
    encoding: {
      color: lineColor("Activity trend"),
      y: { field: "trend", type: "quantitative", axis: null, scale: { domain: [0, 100] } },
    },
  };

  return {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    background: null,
    width: "container",
    height: scaled(260),
    view: { stroke: null },
    config: { font: FONT_STACK },
    data: { values: withTrend(activity) },
    encoding: {
      x: {
        field: "minute",
        type: "quantitative",
        title: null,
        scale: {
          domain,
          nice: false,
          padding: scaled(12),
        },
        axis: {
          ...axisBase,
          grid: false,
          values: axisTicks(domain),
          // Minutes after midnight -> "9am" (or "9:30am" off the hour).
          labelExpr:
            "(floor(datum.value / 60) % 12 || 12) + (datum.value % 60 ? ':' + (datum.value % 60 < 10 ? '0' : '') + datum.value % 60 : '') + (datum.value < 720 ? 'am' : 'pm')",
          labelFontSize: scaled(9),
          labelOverlap: "parity",
        },
      },
    },
    layer: [
      trendLayer,
      measureLayer("sessions", "Sessions", sessionsColor, "left"),
      measureLayer("messages", "Messages", messagesColor, "right"),
    ],
    resolve: { scale: { y: "independent" } },
  };
}

export interface ActivityLineChartProps {
  activity: ActivityBucket[];
}

/** Sessions (left axis) and messages (right axis) by local time of day in 30-minute blocks, as
 *  absolute counts on two independent y scales. The server already trims `activity` to the span
 *  between the first and last block that had any activity. */
export function ActivityLineChart({ activity }: ActivityLineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  const scaled = useScaled();
  const spec = useMemo(
    () => (activity.length === 0 ? null : buildSpec(activity, scaled)),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- theme drives a rebuild for new colors
    [activity, theme, scaled],
  );
  useVegaEmbed(containerRef, spec);

  if (activity.length === 0) return null;

  return (
    <div className="overview-chart">
      <h2 className="chart-heading">Activity by Hour of Day</h2>
      <p className="chart-caption">
        Absolute counts per 30-minute block, by the time a session started: Sessions read against
        the left axis, Messages against the right. The two axes have different scales, so compare
        the shapes of the lines rather than their heights.
      </p>
      <p className="chart-caption">
        <strong>How the Activity trend is calculated:</strong> for each block, Sessions and Messages
        are each turned into a share of their own busiest block (0–100%), then the two shares are
        averaged so both count equally. That series is then smoothed with a moving average over
        three neighbouring blocks (1.5 hours). It's drawn on its own 0–100 scale, so read it as
        "how busy this time of day is compared with the busiest, across both measures", not as a
        count. Its value shows in the tooltip.
      </p>
      <div ref={containerRef} className="bar-chart" role="img" aria-label="Sessions and messages by time of day" />
    </div>
  );
}
