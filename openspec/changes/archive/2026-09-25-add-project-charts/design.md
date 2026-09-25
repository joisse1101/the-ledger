## Context

See proposal.md for motivation and the `web-dashboard` spec delta for required behavior.

- `api/overview_stats.py` is pure Python over `ClaudeTranscript`s: `filter_by_range`, `project_totals`
  (top 7 + "Other", with `share`/`messages_pct`/`cost_pct`), and `time_of_day_activity`. `/api/overview`
  ties them together and the Overview page's donut, bar and line charts render the result.
- `transcript.project` is only the project folder's **basename** (`Path(path).name`), so it is not a
  safe key for "this project". Each transcript does carry its `path`, whose parent folder is the
  sanitized project path (`claude_db.sanitize_project_path`); the delete flow already matches on that
  (`transcript_paths_for_project`).
- `transcript.git_branch` is a single string per transcript: the last `gitBranch` seen in the file
  (`claude_db.py`), `""` when none was recorded.
- `ProjectsList` currently owns the delete flow (row click sets `pending`, an inline `detail-notice`
  confirms). The only modal in the app is `SessionDialog`, a large session-specific native `<dialog>`;
  session delete confirms inline, so there is no reusable confirm dialog.
- Sessions keep their selection in the URL (`?session=<id>`); the same pattern is used here.

## Goals / Non-Goals

**Goals:**
- One aggregation path serves both Overview and the per-project panel; the charts are reused, not
  forked.
- A project is identified by its on-disk folder, never by its display name.

**Non-Goals:**
- KPI summary tiles for a project (not requested; the Overview `summary` is not shown here).
- Converting Sessions' inline `DeleteControls` to the new modal.
- Per-branch drill-down, or attributing a session to more than one branch.

## Decisions

**1. Extend `GET /api/overview` with `project` and `group_by`, rather than add a route.**
`project` is a project path (as returned by `/api/projects`); `group_by` is `project` (default) or
`branch`. The server 404s unless `project` exactly matches a known project (same rule as
`DELETE /api/projects`) and 422s on an unknown `group_by`, then filters transcripts to that project,
applies the range, and groups. The payload is otherwise the shape Overview already returns, so
`useOverview` and its types barely change.
*Alternative:* a separate `/api/projects/overview` route. Cleaner in isolation but duplicates the
payload, the range validation and the empty-state handling.

**2. Match a project's transcripts by folder, in the API.**
A new `filter_by_project(transcripts, folder)` in `overview_stats.py` compares
`transcript.path.parent.name` to the folder; `server.py` computes the folder with
`claude_db.sanitize_project_path(project.path)`. This keeps `overview_stats` free of `claude_db`
(it stays pure over transcripts, like the rest of that module) and matches how delete finds a
project's files.
*Alternative:* filter on `transcript.project == name`. Rejected: two projects with the same basename
would merge, which the spec forbids.

**3. Generalise the group rows: `groups` / `group_order`, each row keyed by `group`.**
`project_totals` becomes `group_totals(transcripts, key)` with `key` a function (project name or
branch label). The response's `projects`/`project_order` and each row's `project` field become
`groups`/`group_order`/`group`, for both Overview and the project panel. Only this repo's own
frontend consumes it and both ship together, so the rename is one coordinated edit (API, `types.ts`,
tests) and avoids a `project` field that actually holds a branch name.
*Alternative:* keep the old names for Overview and add `branches`/`branch_order` for the panel.
Rejected: it forces every chart to take two prop shapes.
The branch key maps `""` to `"(no branch)"`. "Other" and the top-7 cut are unchanged.

**4. Reuse the charts with a `groupLabel` prop; rename the two grouped ones.**
`ProjectDonutChart`/`ProjectBarChart` become `GroupDonutChart`/`GroupBarChart` (`git mv`) taking
`groups`, `groupOrder` and `groupLabel` (`"project"` or `"branch"`), which drive the headings, aria
labels, tooltip titles and the "% of top …" wording. `ActivityLineChart` is already generic and is
used unchanged. `chartTheme`'s color-scale helpers already take an order list, so a branch keeps one
color across both charts.

**5. Panel state lives in the page; the panel is keyed by project.**
`ProjectsPage` reads/writes `?project=<path>` with `useSearchParams`. It renders
`<ProjectDetailPanel key={path} …>`, which owns the time range (`useState`, default "All time").
Keying gives the "range resets on a new project" behavior for free, and stops `keepPreviousData`
showing the previous project's charts under the new one (a fresh observer has no previous data).
`useOverview` gains an optional `{project, groupBy}`; its query key extends the existing
`["overview", range]` prefix, so `useDeleteProject`'s `["overview"]` invalidation still covers it.
A `?project=` value that isn't in the loaded project list is dropped from the URL (deleted, or a stale
link) rather than showing an error.

**6. Split `ProjectsList` into list + panel; delete moves to the panel.**
`ProjectsList` becomes a selection-only list (`selectedPath`, `onSelect`, keeping the `row-selected`
class); selecting works on every device, no longer gated on `is_local`, and the row label stops
saying "to delete". The panel renders the "Delete project" button only when `is_local`, and the
button opens the confirmation modal. On success the panel calls `onDeleted`, and the page clears
`?project=`.

**7. A small generic `ConfirmDialog`, native `<dialog>`, CSS module.**
Props: `open`, `title`, `children` (the body text/path), `confirmLabel`, `pending`, `error`,
`onConfirm`, `onCancel`. Same open/close sync as `SessionDialog` (an effect calls
`showModal()`/`close()`; the component stays mounted). While `pending`, the `cancel` event (Esc) is
`preventDefault`ed, a backdrop click is ignored, and both buttons are disabled; otherwise Esc,
backdrop click and Cancel all call `onCancel`. The error renders inside the dialog and it stays open.
Colours come only from the `tokens.css` variables, per the repo's module convention.
*Alternative:* reuse `SessionDialog`'s styles. Rejected: it is full-screen on narrow viewports and
session-specific.

## Risks / Trade-offs

Each risk is written as: what could go wrong, in plain terms, then what we do about it.

- **Clicking a project row no longer deletes it.**
  *The risk:* anyone used to "click a row to delete" now gets a chart panel instead, which may
  surprise them.
  *What we do:* the delete button lives in that panel, and the confirmation modal shows the exact
  path. Nothing is lost, and a stray click can no longer start a destructive action.

- **A session is counted under the last branch it was on.**
  *The risk:* if you switched branches partway through a session, the whole session is counted under
  the final branch, so a branch's numbers can look slightly off.
  *What we do:* the chart captions and the spec say so. Tracking the branch turn by turn isn't
  worth the extra work here.

- **Renaming the response keys.**
  *The risk:* the server's Overview data currently calls its lists `projects` and `project_order`.
  To reuse them for branches, we rename them to something neutral (`groups`). Anything else reading
  the old names would break.
  *What we do:* only this app's own frontend reads them, and it is updated in the same change, along
  with the API tests, so nothing is left broken.

- **The test environment only half-supports `<dialog>`.**
  *The risk:* the frontend tests run in jsdom, a fake browser that runs in Node. It only partly
  supports the `<dialog>` element's `showModal()` and `close()`, so a test that opens the modal could
  crash.
  *What we do:* add small stand-in versions of those two functions to the test setup file
  (`test-setup.ts`) if they're missing. The tests then check what we control (is it open, are the
  buttons disabled while deleting, is the error shown). They can't check what the real browser does
  for free, such as keeping keyboard focus inside the modal, so that is checked by hand in a real
  browser.

- **A long project list can push the charts off screen.**
  *The risk:* the charts appear under the list. With many projects, clicking one near the top puts
  the charts below the visible area, and it looks like nothing happened.
  *What we do:* scroll the chart panel into view automatically when a project is selected.

- **A branch named "Other" would be mixed into the "Other" bucket.**
  *The risk:* the charts show the top 7 branches and lump the rest into a bucket labelled "Other".
  A real branch literally named `Other` would be merged into that bucket. The same is already true
  of a project named "Other" on Overview. The "(no branch)" label has the same theoretical problem.
  *What we do:* nothing. It is very unlikely, so we are accepting it.
