import { useEffect, useRef } from "react";
import type { Result } from "vega-embed";
import type { Compaction, ContextBreakdown, Turn } from "../../api/types";
import { responseRows, tooltipContent, type TooltipContent } from "../../lib/contextBreakdown";
import { useTheme } from "../../theme/theme";
import { useScaled } from "../../hooks/useScaled";
import type { Scaled } from "../../lib/uiScale";

export interface TokensChartProps {
  turns: Turn[];
  compactions: Compaction[];
  /** When present, hovering a bar shows that response's category breakdown instead of the plain fields. */
  breakdown?: ContextBreakdown | null;
  /** Called with the 1-based response number when a bar is clicked or tapped. */
  onSelect?: (response: number) => void;
}

const KINDS = ["Cache read", "Cache written", "New"] as const;

interface ChartRecord {
  Response: number;
  Kind: (typeof KINDS)[number];
  Tokens: number;
  Output: number;
  Total: number;
}

interface MarkerRecord {
  Response: number;
  Total?: number;
  Note: string;
}

function chartRecords(turns: Turn[]): ChartRecord[] {
  const records: ChartRecord[] = [];
  turns.forEach((turn, index) => {
    const Response = index + 1;
    const Output = turn.output;
    const Total = turn.context;
    records.push({ Response, Kind: "Cache read", Tokens: turn.cache_read, Output, Total });
    records.push({ Response, Kind: "Cache written", Tokens: turn.cache_written, Output, Total });
    records.push({ Response, Kind: "New", Tokens: turn.new, Output, Total });
  });
  return records;
}

function cacheMissRecords(turns: Turn[]): MarkerRecord[] {
  return turns
    .map((turn, index) => ({ Response: index + 1, Total: turn.context, Note: "Cache miss", miss: turn.cache_miss }))
    .filter((r) => r.miss)
    .map(({ Response, Total, Note }) => ({ Response, Total, Note }));
}

function compactionRecords(compactions: Compaction[]): MarkerRecord[] {
  return compactions.map((c) => ({ Response: c.position + 1, Note: "Compaction" }));
}

/** Reads the categorical/text/grid colors this chart needs straight from the theme's CSS
 *  variables, so it stays in sync with tokens.css without duplicating any hex values. */
function themeColors() {
  const style = getComputedStyle(document.documentElement);
  const read = (name: string) => style.getPropertyValue(name).trim();
  return {
    hues: [read("--cat-0"), read("--cat-1"), read("--cat-2")],
    text: read("--text-main"),
    text2: read("--text-muted"),
    grid: read("--border-subtle"),
  };
}

/** The hover content as vega-tooltip markup. Every dynamic string goes through `escape`: tool names
 *  and file labels come from the transcript. */
export function breakdownTooltipHtml(content: TooltipContent, escape: (value: string) => string): string {
  const rows = content.lines
    .map((line) => `<tr><td class="key">${escape(line.name)}:</td><td class="value">${escape(line.value)}</td></tr>`)
    .join("");
  const note = content.estimateNote ? `<tr><td class="key" colspan="2">${escape(content.estimateNote)}</td></tr>` : "";
  return `<h2>${escape(content.title)}</h2><table>${rows}${note}</table>`;
}

/** The tooltip for a value from one of the chart's layers: the breakdown for a bar, the plain
 *  `key: value` rows for the cache-miss and compaction markers. */
function formatChartTooltip(turns: Turn[], breakdown: ContextBreakdown) {
  return (value: unknown, escape: (value: unknown) => string): string => {
    const fields = (value ?? {}) as Record<string, unknown>;
    const response = Number(fields.Response);
    const turn = turns[response - 1];
    if (fields.Note === undefined && turn) {
      const content = tooltipContent(responseRows(breakdown, response - 1), response, turn.context);
      return breakdownTooltipHtml(content, escape);
    }
    const rows = Object.entries(fields)
      .map(([key, field]) => `<tr><td class="key">${escape(key)}:</td><td class="value">${escape(field)}</td></tr>`)
      .join("");
    return `<table>${rows}</table>`;
  };
}

function buildSpec(turns: Turn[], compactions: Compaction[], scaled: Scaled, hasBreakdown: boolean) {
  const { hues, text, text2, grid } = themeColors();
  const count = turns.length;
  const xAxis = {
    domain: false,
    ticks: false,
    labelAngle: 0,
    labelColor: text2,
    labelFontSize: scaled(10),
    labelOverlap: "parity",
    titleColor: text2,
  };
  const x = {
    field: "Response",
    type: "ordinal",
    title: "Response",
    axis: xAxis,
    scale: { domain: Array.from({ length: count }, (_, i) => i + 1) },
  };

  const bars = {
    data: { values: chartRecords(turns) },
    mark: { type: "bar", cursor: hasBreakdown ? "pointer" : undefined },
    encoding: {
      x,
      y: {
        field: "Tokens",
        type: "quantitative",
        title: "Tokens sent",
        axis: {
          domain: false,
          gridColor: grid,
          labelColor: text2,
          labelFontSize: scaled(10),
          titleColor: text2,
          format: "~s",
        },
      },
      color: {
        field: "Kind",
        type: "nominal",
        scale: { domain: KINDS, range: [hues[1], hues[2], hues[0]] },
        legend: { title: null, orient: "top" },
      },
      order: { field: "Kind", sort: "ascending" },
      tooltip: hasBreakdown
        ? [{ field: "Response", type: "ordinal" }]
        : [
            { field: "Response", type: "ordinal" },
            { field: "Kind", type: "nominal" },
            { field: "Tokens", type: "quantitative", format: "," },
            { field: "Total", type: "quantitative", format: ",", title: "Context" },
            { field: "Output", type: "quantitative", format: ",", title: "Output" },
          ],
    },
  };

  const layers: Record<string, unknown>[] = [bars];

  const misses = cacheMissRecords(turns);
  if (misses.length > 0) {
    layers.push({
      data: { values: misses },
      mark: { type: "point", shape: "triangle-down", filled: true, size: scaled(90), color: text, yOffset: -scaled(8) },
      encoding: {
        x,
        y: { field: "Total", type: "quantitative" },
        tooltip: [
          { field: "Response", type: "ordinal" },
          { field: "Note", type: "nominal" },
        ],
      },
    });
  }

  const compactionMarks = compactionRecords(compactions);
  if (compactionMarks.length > 0) {
    layers.push({
      data: { values: compactionMarks },
      mark: { type: "rule", strokeDash: [4, 3], color: text2, strokeWidth: 1.5 },
      encoding: {
        x,
        tooltip: [
          { field: "Response", type: "ordinal" },
          { field: "Note", type: "nominal" },
        ],
      },
    });
  }

  return {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    background: null,
    width: "container",
    height: scaled(260),
    view: { stroke: null },
    config: {
      font: "system-ui, -apple-system, 'Segoe UI', sans-serif",
      legend: { labelColor: text2, labelFontSize: scaled(12) },
    },
    layer: layers,
  };
}

/** Tokens sent per response, stacked by kind. ▼ marks a cache miss (a response that wrote more
 *  cache than it read); a dashed rule marks the response right after a compaction. `vega-embed`
 *  is dynamically imported so the Sessions page doesn't pay for it until a detail view actually
 *  needs it. Colors are read from the theme's CSS variables at embed time and the chart is
 *  re-embedded whenever the theme changes or the data changes; container width changes are
 *  handled by Vega itself (a spec with `width: "container"` sets up its own ResizeObserver). */
export function TokensChart({ turns, compactions, breakdown = null, onSelect }: TokensChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // A ref, so a parent re-render with a new callback doesn't re-embed the chart.
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const { theme } = useTheme();
  const scaled = useScaled();

  useEffect(() => {
    if (turns.length === 0) return;
    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    let result: Result | null = null;

    import("vega-embed").then(({ default: vegaEmbed }) => {
      if (cancelled) return;
      const options = {
        actions: false,
        renderer: "svg" as const,
        ...(breakdown ? { tooltip: { formatTooltip: formatChartTooltip(turns, breakdown) } } : {}),
      };
      vegaEmbed(container, buildSpec(turns, compactions, scaled, breakdown !== null) as never, options as never).then((embedded) => {
        if (cancelled) {
          embedded.finalize();
          return;
        }
        if (breakdown) {
          embedded.view.addEventListener("click", (_event, item) => {
            const response = Number((item?.datum as { Response?: unknown } | undefined)?.Response);
            if (Number.isInteger(response) && response >= 1) onSelectRef.current?.(response);
          });
        }
        result = embedded;
      });
    });

    return () => {
      cancelled = true;
      result?.finalize();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- theme drives a re-embed for new colors
  }, [turns, compactions, breakdown, theme, scaled]);

  if (turns.length === 0) return null;

  return (
    <div
      ref={containerRef}
      className="tokens-chart"
      role="img"
      aria-label="Tokens sent per response, stacked by new, cache written, and cache read tokens"
    />
  );
}
