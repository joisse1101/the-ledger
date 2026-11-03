# Backend: overview and query modules

This page explains the two pure modules behind the Overview numbers and the session list filters: `overview_stats.py` for `/api/overview` and `transcript_query.py` for `/api/transcripts`.

## `overview_stats.py`

### What it is

- `api/app/domain/overview_stats.py` is the pure aggregation behind `/api/overview`.
- It uses no pandas.

### Its pieces

- `TIME_RANGES` are All time, Today, Yesterday, Past week, Past month, Past quarter and Past year.
  - They are bucketed by local calendar date, not a rolling window.
- `filter_by_range` filters by one of those ranges.
- `filter_by_project` matches a transcript's project folder.
  - The folder is `ClaudeTranscript.project_folder`: the on-disk parent folder, or the repo's for a worktree session.
  - It does not match the `project` basename, so two same-named projects never merge.
- `group_totals` groups by a `GROUP_KEYS` key.
  - The keys are project name, git branch, or work stream.
  - The work stream key is `worktree`: `wt <name>`, else the branch.
  - `""` is shown as `"(no branch)"`.
  - It keeps the top 7 plus `"Other"`.
  - It adds `share`, `messages_pct` and `cost_pct`.
- `time_of_day_activity` makes 48 half-hour buckets.
  - They are trimmed to the contiguous active range, zero-filled between.
  - Each row is `{minute, label, sessions, messages}`.
- `format_duration` formats durations.
- `summary()` gives the KPI figures.
  - They include distinct `branches` and `worktrees` counts.
  - Extremes are annotated with `project` and `session_id` via `_with_session`.

### `overview()`

- `overview()` ties it together into the `/api/overview` response.
- The response includes `group_order`.
  - It is the one ordering every chart on the page uses.
  - So a group's color never shifts between charts.
- It takes an optional `project_folder` and a `group_by`.
- So the Overview page and the Projects page's per-project panel share one aggregation path.

## `transcript_query.py`

### What it is

- `api/app/domain/transcript_query.py` is the filter and sort logic behind `/api/transcripts`.

### Its pieces

- `filter_transcripts` does a literal, case-insensitive substring match over session ID, last message and first prompt.
  - It is AND-combined with project, version, branch and worktree membership.
- `sort_transcripts` is stable, with missing values last in either direction.
- `filter_options` gives the distinct non-blank values per filterable field.
- `query()` combines all of that plus paging into a `Page(items, total, options)`.
  - Paging uses `limit` and `offset`.
  - The default page size is 50.
