import type { OverviewSummary } from "../../api/types";
import { formatContext, formatCount } from "../../lib/format";
import { Tooltip } from "../Tooltip";

interface Extreme {
  project: string | null;
  session_id: string | null;
}

interface Tile {
  label: string;
  value: string;
  /** Present only for the longest/shortest/most-expensive/cheapest figures. */
  extreme?: Extreme;
}

function tiles(summary: OverviewSummary): Tile[] {
  return [
    { label: "Projects", value: formatCount(summary.projects) },
    { label: "Sessions", value: formatCount(summary.sessions) },
    { label: "Messages", value: formatCount(summary.messages) },
    {
      label: "Avg. messages / session",
      value: summary.avg_messages_per_session != null ? summary.avg_messages_per_session.toFixed(1) : "--",
    },

    { label: "Avg. session", value: summary.duration.average.label },
    { label: "Total duration", value: summary.duration.total.label },
    { label: "Longest session", value: summary.duration.longest.label, extreme: summary.duration.longest },
    { label: "Shortest session", value: summary.duration.shortest.label, extreme: summary.duration.shortest },

    { label: "Avg. session cost", value: summary.cost.average.label },
    { label: "Total cost", value: summary.cost.total.label },
    { label: "Most expensive session", value: summary.cost.most_expensive.label, extreme: summary.cost.most_expensive },
    { label: "Cheapest session", value: summary.cost.cheapest.label, extreme: summary.cost.cheapest },

    { label: "Avg. tokens / session", value: formatContext(summary.tokens.average) },
    { label: "Total tokens", value: formatContext(summary.tokens.total) },
    { label: "Most tokens", value: formatContext(summary.tokens.most.amount), extreme: summary.tokens.most },
    { label: "Least tokens", value: formatContext(summary.tokens.least.amount), extreme: summary.tokens.least },
  ];
}

function extremeNote(extreme: Extreme): string | null {
  return extreme.project && extreme.session_id ? `${extreme.project} — ${extreme.session_id}` : null;
}

export interface SummaryStatsProps {
  summary: OverviewSummary;
}

/** The Overview KPI grid: counts, session-duration, session-cost, and context-token figures for the
 *  selected time range. The six extreme figures (longest/shortest/most-expensive/cheapest/most-tokens/
 *  least-tokens) carry a tooltip naming the project and session they belong to. */
export function SummaryStats({ summary }: SummaryStatsProps) {
  return (
    <div className="stat-grid">
      {tiles(summary).map(({ label, value, extreme }) => {
        const note = extreme && extremeNote(extreme);
        return (
          <div key={label} className="stat-tile">
            <span className="stat-label">
              {label}
              {note && <Tooltip tooltip={note} size="sm" />}
            </span>
            <span className="stat-value">{value}</span>
          </div>
        );
      })}
    </div>
  );
}
