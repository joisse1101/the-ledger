import { useProjects } from "../../api/queries";
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

export interface ProjectsListProps {
  /** Path of the selected project, if any; its row is accented. */
  selectedPath: string | null;
  onSelect: (project: Project) => void;
}

/** The Projects page's list: every project Claude Code has been run or trusted in. Selecting a row
 *  only reports the choice (the page shows that project's charts); it never deletes anything, and
 *  it works on every device. */
export function ProjectsList({ selectedPath, onSelect }: ProjectsListProps) {
  const projects = useProjects();
  const rows = projects.data?.projects ?? [];

  return (
    <section aria-label="Projects">
      <ResponsiveList
        columns={columns}
        rows={rows}
        rowId={(p) => p.path}
        onSelect={onSelect}
        rowLabel={(p) => `Select project ${p.name}`}
        emptyMessage="No Claude projects found."
        ariaLabel="Projects"
        rowClassName={(p) => (p.path === selectedPath ? "row-selected" : undefined)}
      />
    </section>
  );
}
