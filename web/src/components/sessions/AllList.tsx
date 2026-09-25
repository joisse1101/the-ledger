import { useMemo, useState } from "react";
import { useTranscripts } from "../../api/queries";
import type { SortDirection, SortField, TranscriptItem } from "../../api/types";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useViewportClass } from "../../hooks/useViewportClass";
import { formatContext, formatCost, formatCount, formatDateTime, formatText } from "../../lib/format";
import { ResponsiveList } from "../list/ResponsiveList";
import type { ListColumn } from "../list/types";
import { FilterMultiselect } from "./FilterMultiselect";

const columns: ListColumn<TranscriptItem>[] = [
  { key: "project", header: "Project", priority: "high", sortKey: "project", render: (t) => formatText(t.project) },
  { key: "title", header: "Title", priority: "high", sortKey: "title", render: (t) => formatText(t.title) },
  {
    key: "updated_at",
    header: "Updated",
    priority: "high",
    sortKey: "updated_at",
    render: (t) => formatDateTime(t.updated_at),
  },
  {
    key: "started_at",
    header: "Started",
    priority: "low",
    cardPriority: "secondary",
    sortKey: "started_at",
    render: (t) => formatDateTime(t.started_at),
  },
  {
    key: "message_count",
    header: "Messages",
    priority: "high",
    align: "end",
    cardPriority: "secondary",
    sortKey: "message_count",
    render: (t) => formatCount(t.message_count),
  },
  {
    key: "cost",
    header: "Cost",
    priority: "high",
    align: "end",
    cardPriority: "secondary",
    sortKey: "cost",
    render: (t) => formatCost(t.cost),
  },
  {
    key: "context",
    header: "Context",
    priority: "high",
    align: "end",
    sortKey: "context",
    render: (t) => formatContext(t.context),
  },
  {
    key: "version",
    header: "Version",
    priority: "low",
    cardPriority: "hidden",
    sortKey: "version",
    render: (t) => formatText(t.version),
  },
  {
    key: "git_branch",
    header: "Branch",
    priority: "low",
    cardPriority: "secondary",
    sortKey: "git_branch",
    render: (t) => formatText(t.git_branch),
  },
  {
    key: "session_id",
    header: "Session ID",
    priority: "low",
    cardPriority: "hidden",
    sortKey: "session_id",
    render: (t) => <code>{t.session_id}</code>,
  },
  {
    key: "live",
    header: "Live",
    priority: "high",
    cardPriority: "hidden",
    render: (t) => (t.live ? <span className="live-badge">Live</span> : null),
  },
];

const sortableColumns = columns.filter((column) => column.sortKey);

export interface AllListProps {
  onSelect: (session: TranscriptItem) => void;
}

/** The Sessions page's "All" list: debounced search, Project/Version/Branch filters, sortable
 *  columns (a "Sort by" select on narrow screens, since cards have no headers), and 50-at-a-time
 *  paging via "Load more". */
export function AllList({ onSelect }: AllListProps) {
  const viewport = useViewportClass();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [projects, setProjects] = useState<string[]>([]);
  const [versions, setVersions] = useState<string[]>([]);
  const [branches, setBranches] = useState<string[]>([]);
  const [sortField, setSortField] = useState<SortField>("updated_at");
  const [sortDir, setSortDir] = useState<SortDirection>("desc");

  const query = useMemo(
    () => ({
      q: debouncedSearch.trim() || undefined,
      project: projects.length ? projects : undefined,
      version: versions.length ? versions : undefined,
      branch: branches.length ? branches : undefined,
      sort: sortField,
      dir: sortDir,
    }),
    [debouncedSearch, projects, versions, branches, sortField, sortDir],
  );

  const transcripts = useTranscripts(query);

  const pages = transcripts.data?.pages ?? [];
  const rows = pages.flatMap((page) => page.items);
  const total = pages[0]?.total ?? 0;
  const options = pages[0]?.options ?? { projects: [], versions: [], branches: [] };

  const handleSortChange = (field: string) => {
    if (field === sortField) {
      setSortDir((dir) => (dir === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field as SortField);
      setSortDir("asc");
    }
  };

  return (
    <section aria-label="All sessions">
      <div className="sessions-filters">
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search session ID, last message, or prompt"
          aria-label="Search sessions"
          className="sessions-search"
        />
        <div className="filter-multiselect-container">
          <FilterMultiselect label="Project" options={options.projects} selected={projects} onChange={setProjects} />
          <FilterMultiselect label="Version" options={options.versions} selected={versions} onChange={setVersions} />
          <FilterMultiselect label="Branch" options={options.branches} selected={branches} onChange={setBranches} />
        </div>
      </div>

      {viewport === "narrow" && (
        <div className="sort-field">
          <label className="sort-field-label">
            Sort by
            <select value={sortField} onChange={(event) => setSortField(event.target.value as SortField)}>
              {sortableColumns.map((column) => (
                <option key={column.sortKey} value={column.sortKey}>
                  {column.header}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="icon-button"
            onClick={() => setSortDir((dir) => (dir === "asc" ? "desc" : "asc"))}
            aria-label={sortDir === "asc" ? "Sort ascending" : "Sort descending"}
          >
            {sortDir === "asc" ? "▲" : "▼"}
          </button>
        </div>
      )}

      <ResponsiveList
        columns={columns}
        rows={rows}
        rowId={(t) => t.session_id}
        onSelect={onSelect}
        emptyMessage="No sessions match the current filters."
        ariaLabel="All sessions"
        sort={{ field: sortField, dir: sortDir, onChange: handleSortChange }}
        rowClassName={(t) => (t.live ? "row-live" : undefined)}
        rowBadge={(t) => (t.live ? <span className="live-badge">Live</span> : null)}
      />

      {rows.length > 0 && (
        <div className="sessions-load-more">
          <span className="muted">
            Showing {rows.length} of {total}
          </span>
          {transcripts.hasNextPage && (
            <button
              type="button"
              className="button"
              onClick={() => transcripts.fetchNextPage()}
              disabled={transcripts.isFetchingNextPage}
            >
              {transcripts.isFetchingNextPage ? "Loading…" : "Load more"}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
