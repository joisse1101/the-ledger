import { useEffect, useMemo, useRef, type ReactNode } from "react";
import { useProjectRepos, useProjects } from "../../api/queries";
import type { Project, ProjectRepo } from "../../api/types";
import { formatCost, formatCount, formatDateTime, formatText } from "../../lib/format";
import { ResponsiveList } from "../list/ResponsiveList";
import type { ListColumn } from "../list/types";

function linesChanged(project: Project): string {
  if (project.lines_added == null && project.lines_removed == null) return "--";
  return `+${formatCount(project.lines_added ?? 0)}/-${formatCount(project.lines_removed ?? 0)}`;
}

type RepoByPath = ReadonlyMap<string, ProjectRepo>;

/** Issue and PR counts, or `--` while they load and whenever they can't be known. */
function repoCount(count: number | null | undefined): string {
  return count == null ? "--" : formatCount(count);
}

function sourceLabel(repo: ProjectRepo | undefined): string {
  return repo?.host ?? "--";
}

/** The host name as a link to the repo's page. Clicking it must not also toggle the row. */
function sourceLink(repo: ProjectRepo | undefined): ReactNode {
  if (!repo?.url || !repo.host) return "--";
  return (
    <a href={repo.url} target="_blank" rel="noopener noreferrer" onClick={(event) => event.stopPropagation()}>
      {repo.host}
    </a>
  );
}

function buildColumns(repoByPath: RepoByPath): ListColumn<Project>[] {
  return [
    { key: "name", header: "Name", priority: "high", render: (p) => formatText(p.name) },
    { key: "path", header: "Path", priority: "high", cardPriority: "secondary", render: (p) => <code>{p.path}</code> },
    {
      key: "source",
      header: "Source",
      priority: "low",
      render: (p) => sourceLink(repoByPath.get(p.path)),
      // A card is one button, so the link is plain text there; the panel's "Open project" is the link.
      renderCard: (p) => sourceLabel(repoByPath.get(p.path)),
    },
    {
      key: "issues",
      header: "Issues",
      priority: "low",
      align: "end",
      render: (p) => repoCount(repoByPath.get(p.path)?.issues),
    },
    {
      key: "prs",
      header: "PRs",
      priority: "low",
      align: "end",
      render: (p) => repoCount(repoByPath.get(p.path)?.prs),
    },
    ...otherColumns,
  ];
}

const otherColumns: ListColumn<Project>[] = [
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
  /** Paths of the projects currently expanded; any number can be open at once, each accented and
   *  showing `renderExpanded`'s content inline beneath its row. */
  expandedPaths: Set<string>;
  /** Clicking a row toggles whether that project's panel is open. */
  onToggle: (project: Project) => void;
  /** The panel rendered inline beneath an expanded project's row. */
  renderExpanded: (project: Project) => ReactNode;
}

/** The Projects page's list: every project Claude Code has been run or trusted in. Clicking a row
 *  opens or closes that project's detail panel directly beneath it - it never deletes anything,
 *  and it works on every device. */
export function ProjectsList({ expandedPaths, onToggle, renderExpanded }: ProjectsListProps) {
  const projects = useProjects();
  const rows = projects.data?.projects ?? [];
  const repos = useProjectRepos().data?.repos;
  const columns = useMemo(() => buildColumns(new Map((repos ?? []).map((repo) => [repo.path, repo]))), [repos]);
  const sectionRef = useRef<HTMLElement>(null);
  // The path a click just opened, so the effect below knows which row to scroll to once its panel
  // has actually rendered - closing a row, or a re-render for any other reason, scrolls nothing.
  const pendingScrollPath = useRef<string | null>(null);

  const handleSelect = (project: Project) => {
    if (!expandedPaths.has(project.path)) pendingScrollPath.current = project.path;
    onToggle(project);
  };

  useEffect(() => {
    const path = pendingScrollPath.current;
    if (path === null || !expandedPaths.has(path)) return;
    pendingScrollPath.current = null;
    const row = Array.from(sectionRef.current?.querySelectorAll<HTMLElement>("[data-row-id]") ?? []).find(
      (el) => el.dataset.rowId === path,
    );
    if (!row) return;

    const scrollRowIntoView = () => row.scrollIntoView?.({ block: "start", behavior: "smooth" });
    scrollRowIntoView();

    // The row's own position doesn't move once its panel (the very next sibling) starts rendering
    // beneath it, but the panel's content (the overview query, then its charts) can still be
    // loading at that first scroll - the page isn't tall enough yet for the browser to bring the
    // row all the way to the top. Keep re-scrolling as the panel grows until it settles.
    const panel = row.nextElementSibling;
    if (!panel) return;
    const observer = new ResizeObserver(scrollRowIntoView);
    observer.observe(panel);
    const stopWatching = window.setTimeout(() => observer.disconnect(), 2000);
    return () => {
      observer.disconnect();
      window.clearTimeout(stopWatching);
    };
  }, [expandedPaths]);

  return (
    <section aria-label="Projects" ref={sectionRef}>
      <ResponsiveList
        columns={columns}
        rows={rows}
        rowId={(p) => p.path}
        onSelect={handleSelect}
        rowLabel={(p) => `${expandedPaths.has(p.path) ? "Hide" : "Show"} details for ${p.name}`}
        emptyMessage="No Claude projects found."
        ariaLabel="Projects"
        rowClassName={(p) => (expandedPaths.has(p.path) ? "row-selected" : undefined)}
        expandedIds={expandedPaths}
        renderExpanded={renderExpanded}
      />
    </section>
  );
}
