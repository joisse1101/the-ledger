import { useState } from "react";
import { useLive } from "../../api/queries";
import { formatText, formatTime } from "../../lib/format";
import type { ListColumn } from "../list/types";
import { ResponsiveList } from "../list/ResponsiveList";
import type { LiveSession } from "../../api/types";

const columns: ListColumn<LiveSession>[] = [
  {
    key: "project",
    header: "Project",
    priority: "high",
    render: (s) => formatText(s.project),
  },
  {
    key: "name",
    header: "Name",
    priority: "high",
    cardPriority: "hidden",
    render: (s) => formatText(s.name),
  },
  {
    key: "title",
    header: "Title",
    priority: "high",
    render: (s) => formatText(s.title || s.name),
  },
  {
    key: "status",
    header: "Status",
    priority: "high",
    render: (s) => formatText(s.status),
  },
  {
    key: "kind",
    header: "Kind",
    priority: "low",
    cardPriority: "hidden",
    render: (s) => formatText(s.kind),
  },
  {
    key: "pid",
    header: "PID",
    priority: "low",
    cardPriority: "hidden",
    align: "end",
    render: (s) => String(s.pid),
  },
  {
    key: "context",
    header: "Context",
    priority: "high",
    render: (s) => s.context?.label ?? "--",
  },
  {
    key: "session_id",
    header: "Session ID",
    priority: "low",
    cardPriority: "hidden",
    render: (s) => <code>{s.session_id}</code>,
  },
];

export interface LiveListProps {
  onSelect: (session: LiveSession) => void;
}

/** The Sessions page's "Live" list: polls every 2s, with an Auto-refresh switch and a
 *  frozen "last refreshed" caption while it's off. */
export function LiveList({ onSelect }: LiveListProps) {
  const [auto, setAuto] = useState(true);
  const live = useLive({ auto });

  const lastRefreshed = live.dataUpdatedAt ? new Date(live.dataUpdatedAt).toISOString() : null;

  return (
    <section aria-label="Live sessions">
      <div className="sessions-toolbar">
        <label className="switch-field">
          <input
            type="checkbox"
            checked={auto}
            onChange={(event) => setAuto(event.target.checked)}
          />
          <span>Auto-refresh</span>
        </label>
        <span className="muted sessions-toolbar-caption">
          Last refreshed: <time dateTime={lastRefreshed ?? undefined}>{formatTime(lastRefreshed)}</time>
        </span>
      </div>
      <ResponsiveList
        columns={columns}
        rows={live.data?.sessions ?? []}
        rowId={(s) => s.session_id}
        onSelect={onSelect}
        emptyMessage="No live sessions. Start a Claude Code session to see it here."
        ariaLabel="Live sessions"
      />
    </section>
  );
}
