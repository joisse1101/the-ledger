import { useState } from "react";
import { useLive, useMeta } from "../../api/queries";
import { formatText, formatTime } from "../../lib/format";
import type { ListColumn } from "../list/types";
import { ResponsiveList } from "../list/ResponsiveList";
import { QUESTION_TOOL } from "../../api/types";
import type { LiveSession } from "../../api/types";
import { RemoteModeControl } from "./RemoteModeControl";
import { Switch } from "../Switch";

/** Shown on a row whose session is blocked on a permission prompt or a question, so it's visible
 *  without opening the control view. */
function PendingBadge({ session }: { session: LiveSession }) {
  const pending = session.pending_decision;
  if (!pending) return null;
  return (
    <span className="pending-badge">
      {pending.tool_name === QUESTION_TOOL ? "Asking a question" : `Needs decision: ${pending.tool_name}`}
    </span>
  );
}

/** The card-only marker for a session that auto-approves (its table column is hidden on a card). */
function AutoApproveBadge({ session }: { session: LiveSession }) {
  return session.auto_approve ? <span className="pending-badge">Auto-approve</span> : null;
}

const baseColumns: ListColumn<LiveSession>[] = [
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
    render: (s) => formatText(s.title),
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
    key: "pending_decision",
    header: "Decision",
    priority: "high",
    cardPriority: "hidden",
    render: (s) => <PendingBadge session={s} />,
  },
  {
    key: "session_id",
    header: "Session ID",
    priority: "low",
    cardPriority: "hidden",
    render: (s) => <code>{s.session_id}</code>,
  },
];

const autoApproveColumn: ListColumn<LiveSession> = {
  key: "auto_approve",
  header: "Auto-approve",
  priority: "high",
  cardPriority: "hidden",
  render: (s) => (s.auto_approve ? "On" : ""),
};

/** The Auto-approve column joins only once a prompt has been relayed (before that, the feature is
 *  offered nowhere), and only in this list. */
function columnsFor(relayHookSeen: boolean): ListColumn<LiveSession>[] {
  if (!relayHookSeen) return baseColumns;
  const afterDecision = baseColumns.findIndex((column) => column.key === "pending_decision") + 1;
  return [...baseColumns.slice(0, afterDecision), autoApproveColumn, ...baseColumns.slice(afterDecision)];
}

export interface LiveListProps {
  onSelect: (session: LiveSession) => void;
}

/** The Sessions page's "Live" list: polls every 2s, with an Auto-refresh switch and a
 *  frozen "last refreshed" caption while it's off. */
export function LiveList({ onSelect }: LiveListProps) {
  const [auto, setAuto] = useState(true);
  const live = useLive({ auto });
  const relayHookSeen = useMeta().data?.relay_hook_seen === true;

  const lastRefreshed = live.dataUpdatedAt ? new Date(live.dataUpdatedAt).toISOString() : null;

  return (
    <section aria-label="Live sessions">
      <div className="sessions-toolbar">
        <div className="sessions-toolbar-controls">
          <Switch
            size="sm"
            checked={auto}
            onChange={setAuto}
            label="Auto-refresh"
            tooltip="Automatically refresh the list every 2 seconds"
          />
          <RemoteModeControl />
        </div>
        <span className="muted sessions-toolbar-caption">
          Last refreshed: <time dateTime={lastRefreshed ?? undefined}>{formatTime(lastRefreshed)}</time>
        </span>
      </div>
      <ResponsiveList
        columns={columnsFor(relayHookSeen)}
        rows={live.data?.sessions ?? []}
        rowId={(s) => s.session_id}
        onSelect={onSelect}
        rowBadge={(s) => (
          <>
            <PendingBadge session={s} />
            {relayHookSeen && <AutoApproveBadge session={s} />}
          </>
        )}
        emptyMessage="No live sessions. Start a Claude Code session to see it here."
        ariaLabel="Live sessions"
      />
    </section>
  );
}
