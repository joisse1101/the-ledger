import type { ReactNode } from "react";
import { Tooltip } from "./Tooltip";

/** Names the session a tile's figure came from, for a tooltip. */
export interface SessionRef {
  project: string | null;
  session_id: string | null;
}

export interface StatTile {
  label: string;
  /** A plain string, or a small node such as `CostFigure` for a mark like an estimate asterisk. */
  value: ReactNode;
  /** Present only for a tile naming an extreme session (e.g. longest/most expensive). */
  ref?: SessionRef;
}

/** `project — session_id`, or null when either half is missing. */
export function sessionNote(ref: SessionRef): string | null {
  return ref.project && ref.session_id ? `${ref.project} — ${ref.session_id}` : null;
}

export interface StatGridProps {
  tiles: StatTile[];
}

/** A grid of labelled KPI tiles, shared by Overview's `SummaryStats` and the Projects panel's
 *  `ProjectSummaryStats`. A tile with `ref` carries a tooltip naming the session it came from. */
export function StatGrid({ tiles }: StatGridProps) {
  return (
    <div className="stat-grid">
      {tiles.map(({ label, value, ref }) => {
        const note = ref && sessionNote(ref);
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
