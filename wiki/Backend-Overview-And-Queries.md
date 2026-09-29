# Backend: overview and query modules

- `api/overview_stats.py` — the pure aggregation behind `/api/overview`, no pandas: `TIME_RANGES`
  (All time/Today/Yesterday/Past week/Past month/Past quarter/Past year, bucketed by *local calendar
  date*, not a rolling window), `filter_by_range`, `filter_by_project` (matches a transcript's
  on-disk parent folder, `path.parent.name`, not its `project` basename, so two same-named projects
  never merge), `group_totals` (grouped by a `GROUP_KEYS` key — project name or git branch, `""`
  shown as `"(no branch)"`; top-7 + `"Other"`, `share`/`messages_pct`/`cost_pct`), `time_of_day_activity` (48 half-hour buckets trimmed to the contiguous
  active range, zero-filled between; each row is `{minute, label, sessions, messages}`), `format_duration`, and `summary()` (the KPI figures,
  extremes annotated with `project`/`session_id` via `_with_session`). `overview()` ties it together
  into the `/api/overview` response, including `group_order` — the one ordering every chart on the
  page uses so a group's color never shifts between them. `overview()` takes an optional
  `project_folder` and a `group_by`, so the Overview page and the Projects page's per-project panel
  share one aggregation path.
- `api/transcript_query.py` — the filter/sort logic behind `/api/transcripts`: `filter_transcripts`
  (literal case-insensitive substring over session ID/last message/first prompt, AND-combined with
  project/version/branch membership), `sort_transcripts` (stable, missing values last either
  direction), `filter_options` (distinct non-blank values per filterable field), and `query()` which
  combines all of that plus paging (`limit`/`offset`, default page size 50) into a
  `Page(items, total, options)`.
