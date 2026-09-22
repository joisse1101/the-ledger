import { useState } from "react";
import type { OverviewSummary } from "../../api/types";
import { formatCount } from "../../lib/format";

interface Extreme {
  label: string;
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
    { label: "Longest session", value: summary.duration.longest.label, extreme: summary.duration.longest },
    { label: "Shortest session", value: summary.duration.shortest.label, extreme: summary.duration.shortest },
    { label: "Total duration", value: summary.duration.total.label },
    { label: "Avg. session cost", value: summary.cost.average.label },
    { label: "Most expensive session", value: summary.cost.most_expensive.label, extreme: summary.cost.most_expensive },
    { label: "Cheapest session", value: summary.cost.cheapest.label, extreme: summary.cost.cheapest },
    { label: "Total cost", value: summary.cost.total.label },
  ];
}

function extremeNote(extreme: Extreme): string | null {
  return extreme.project && extreme.session_id ? `${extreme.project} — ${extreme.session_id}` : null;
}

/** A figure that also names which session it came from: a `title` attribute covers hover on a
 *  pointer device, and tapping toggles the same text inline for touch (no hover to rely on). */
function ExtremeStatTile({ label, value, extreme }: { label: string; value: string; extreme: Extreme }) {
  const [open, setOpen] = useState(false);
  const note = extremeNote(extreme);

  return (
    <button
      type="button"
      className="stat-tile stat-tile-button"
      onClick={() => setOpen((current) => !current)}
      aria-expanded={open}
      title={note ?? undefined}
    >
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {open && note && <span className="stat-note">{note}</span>}
    </button>
  );
}

export interface SummaryStatsProps {
  summary: OverviewSummary;
}

/** The Overview KPI grid: counts, session-duration figures, and session-cost figures for the
 *  selected time range. The four extreme figures (longest/shortest/most-expensive/cheapest) are
 *  buttons that reveal which project and session they belong to. */
export function SummaryStats({ summary }: SummaryStatsProps) {
  return (
    <div className="stat-grid">
      {tiles(summary).map((tile) =>
        tile.extreme ? (
          <ExtremeStatTile key={tile.label} label={tile.label} value={tile.value} extreme={tile.extreme} />
        ) : (
          <div key={tile.label} className="stat-tile">
            <span className="stat-label">{tile.label}</span>
            <span className="stat-value">{tile.value}</span>
          </div>
        ),
      )}
    </div>
  );
}
