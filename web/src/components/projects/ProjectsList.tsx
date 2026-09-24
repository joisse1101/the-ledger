import { useState } from "react";
import { useDeleteProject, useMeta, useProjects } from "../../api/queries";
import type { Project } from "../../api/types";
import { formatCost, formatCount, formatDateTime, formatText } from "../../lib/format";
import { ResponsiveList } from "../list/ResponsiveList";
import type { ListColumn } from "../list/types";

function linesChanged(project: Project): string {
  if (project.lines_added == null && project.lines_removed == null) return "--";
  return `+${formatCount(project.lines_added ?? 0)}/-${formatCount(project.lines_removed ?? 0)}`;
}

const columns: ListColumn<Project>[] = [
  { key: "name", header: "Name", priority: "high", render: (p) => formatText(p.name) },
  { key: "path", header: "Path", priority: "high", cardPriority: "secondary", render: (p) => <code>{p.path}</code> },
  {
    key: "trust_accepted",
    header: "Trusted",
    priority: "low",
    cardPriority: "secondary",
    render: (p) => (p.trust_accepted ? "Trusted" : "Not trusted"),
  },
  {
    key: "last_session_id",
    header: "Last Session",
    priority: "low",
    cardPriority: "hidden",
    render: (p) => (p.last_session_id ? <code>{p.last_session_id}</code> : "--"),
  },
  { key: "last_version", header: "Version", priority: "low", cardPriority: "secondary", render: (p) => formatText(p.last_version) },
  {
    key: "last_cost",
    header: "Last Cost",
    priority: "high",
    align: "end",
    cardPriority: "secondary",
    render: (p) => formatCost(p.last_cost),
  },
  {
    key: "last_start_time",
    header: "Last Started",
    priority: "high",
    cardPriority: "secondary",
    render: (p) => formatDateTime(p.last_start_time),
  },
  { key: "lines", header: "Lines +/-", priority: "low", cardPriority: "secondary", render: linesChanged },
  {
    key: "mcp_servers",
    header: "MCP Servers",
    priority: "low",
    cardPriority: "hidden",
    render: (p) => (p.mcp_servers.length ? p.mcp_servers.join(", ") : "--"),
  },
];

/** The Projects page's list: every project Claude Code has been run or trusted in, plus a
 *  select-a-row-to-delete flow (there's no other per-project action here, unlike Sessions'
 *  detail dialog, so selecting a row doubles as "I want to delete this one"). Confirming removes
 *  the entry from ~/.claude.json and its on-disk transcripts, then refetches projects, the All
 *  sessions list, and Overview (wired into useDeleteProject's onSuccess). */
export function ProjectsList() {
  const projects = useProjects();
  const deleteProject = useDeleteProject();
  // Deletes are local-only server-side; on any other device the list is read-only (and stays
  // that way until /api/meta says otherwise).
  const isLocal = useMeta().data?.is_local === true;
  const [pending, setPending] = useState<Project | null>(null);

  const rows = projects.data?.projects ?? [];

  // Selecting a row only ever starts a delete, so it does nothing off the local machine.
  const handleSelect = (project: Project) => {
    if (isLocal) setPending(project);
  };

  const handleConfirm = () => {
    if (!pending) return;
    deleteProject.mutate(pending.path, { onSuccess: () => setPending(null) });
  };

  return (
    <section aria-label="Projects">
      <ResponsiveList
        columns={columns}
        rows={rows}
        rowId={(p) => p.path}
        onSelect={handleSelect}
        emptyMessage="No Claude projects found."
        ariaLabel="Projects"
        rowClassName={(p) => (pending && p.path === pending.path ? "row-selected" : undefined)}
      />

      {isLocal && pending && (
        <div className="detail-notice">
          <p>
            Delete project <code>{pending.path}</code> from ~/.claude.json and remove all of its on-disk session
            transcripts? This cannot be undone.
          </p>
          <div className="detail-actions">
            <button
              type="button"
              className="button button-danger"
              disabled={deleteProject.isPending}
              onClick={handleConfirm}
            >
              {deleteProject.isPending ? "Deleting…" : "Confirm delete"}
            </button>
            <button
              type="button"
              className="button"
              disabled={deleteProject.isPending}
              onClick={() => setPending(null)}
            >
              Cancel
            </button>
          </div>
          {deleteProject.isError && <p className="detail-caption">{deleteProject.error.message}</p>}
        </div>
      )}
    </section>
  );
}
