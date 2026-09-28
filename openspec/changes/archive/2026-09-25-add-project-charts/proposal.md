## Why

The Projects page is a bare list, and its only interaction is "click a row to delete it". There is no
way to see how a single project has actually been used: which branches its sessions ran on, what they
cost, or when in the day the work happened. Overview answers those questions for everything at once;
this gives the same view scoped to one project.

## What Changes

- Selecting a project on the Projects page shows charts for that project only, inline under the list,
  with the selection kept in the address (`?project=<path>`) so a reload or shared link reopens it.
- The charts mirror Overview's, regrouped by branch instead of by project:
  - sessions per branch (donut),
  - messages and cost per branch (grouped bars, each measure as a % of its own peak),
  - activity by hour of day for that project's sessions (the existing dual-axis line chart).
- The same time ranges as Overview (All time, Today, Yesterday, Past week, Past month, Past quarter,
  Past year), defaulting to All time and resetting when a different project is selected.
- **BREAKING (behavior):** clicking a project row no longer starts a delete. Delete becomes an
  explicit "Delete project" button in the selected project's panel, and it opens a confirmation modal
  (naming the project path, stating it can't be undone) instead of the inline notice. Still local-only.
- `GET /api/overview` gains optional `project` and `group_by` parameters so the existing aggregation
  serves both pages. A project's transcripts are matched by on-disk folder, not by folder name, so two
  projects with the same basename are not merged.
- A small reusable `ConfirmDialog` (native `<dialog>`) is added for the delete confirmation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-dashboard`: the "Projects page lists and deletes projects" requirement changes (row click
  selects instead of deleting; delete is a button with a confirmation modal), and a new requirement
  covers the per-project charts and their time range. The Overview time-range requirement is
  referenced, not changed.

## Impact

- **API:** `api/overview_stats.py` (parameterised grouping key, project filter), `api/server.py`
  (`/api/overview` parameters, 404/422 handling for an unknown project or `group_by`), and their tests
  (`test_overview_stats.py`, `test_api_data.py`).
- **Web:** `pages/ProjectsPage.tsx`, `components/projects/ProjectsList.tsx` (+ its tests), a new
  project-detail panel, a new `components/ConfirmDialog`, the Overview donut/bar/line chart components
  (group label made a prop rather than hardcoded "project"), `api/queries.ts` / `api/types.ts`.
- **Docs:** `CLAUDE.md` (Projects section, routes table, test list) and the `web-dashboard` spec.
- No new dependencies, no change to authentication: deletes remain local-only server-side, and the
  new delete button and modal are shown only when `is_local`.
- `DeleteControls` on the Sessions detail dialog is left as is.
