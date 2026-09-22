import type { Turn } from "../../api/types";

export interface TokensChartProps {
  turns: Turn[];
}

// Stack order bottom-to-top matches views/sessions_context.py's _KINDS, and the colors match
// its hues[1]/hues[2]/hues[0] mapping so this and the vega-embed version task 6.5 swaps in read
// the same way.
const SEGMENTS: { key: "new" | "cache_written" | "cache_read"; label: string; colorVar: string }[] = [
  { key: "new", label: "New", colorVar: "--cat-0" },
  { key: "cache_written", label: "Cache written", colorVar: "--cat-2" },
  { key: "cache_read", label: "Cache read", colorVar: "--cat-1" },
];

const BAR_MAX_HEIGHT = 200;

/** Tokens sent per response, stacked by kind. A plain CSS bar for now; task 6.5 replaces the
 *  bars with the ported vega-embed chart (cache-miss markers, dashed compaction rules) without
 *  changing this component's role in the dialog. */
export function TokensChart({ turns }: TokensChartProps) {
  if (turns.length === 0) return null;

  const maxTotal = Math.max(...turns.map((t) => t.new + t.cache_written + t.cache_read), 1);

  return (
    <div
      className="tokens-chart"
      role="img"
      aria-label="Tokens sent per response, stacked by new, cache written, and cache read tokens"
    >
      <div className="tokens-chart-bars">
        {turns.map((turn, index) => (
          <div key={turn.message_id} className="tokens-chart-bar">
            {SEGMENTS.map(({ key, label, colorVar }) => {
              const value = turn[key];
              if (value <= 0) return null;
              const height = Math.max((value / maxTotal) * BAR_MAX_HEIGHT, 1);
              return (
                <div
                  key={key}
                  className="tokens-chart-segment"
                  style={{ height, background: `var(${colorVar})` }}
                  title={`Response ${index + 1} — ${label}: ${value.toLocaleString()}`}
                />
              );
            })}
          </div>
        ))}
      </div>
      <div className="tokens-chart-legend">
        {SEGMENTS.map(({ key, label, colorVar }) => (
          <span key={key} className="tokens-chart-legend-item">
            <span className="tokens-chart-swatch" style={{ background: `var(${colorVar})` }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
