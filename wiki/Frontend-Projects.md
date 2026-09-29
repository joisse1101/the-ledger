# Frontend: projects

> Requirements live in `openspec/specs/web-dashboard/spec.md`. This page describes how the code meets them, not what it must do.

- **Projects** (`web/src/components/projects/ProjectsList.tsx`, `ProjectDetailPanel.tsx`,
  `web/src/pages/ProjectsPage.tsx`): `ProjectsList` renders every field from `useProjects()` (name, path,
  trust, last session, version, last cost, last start, lines +/-, MCP servers) through the same
  `ResponsiveList` the Sessions lists use, as a selection-only list (`selectedPath`/`onSelect`,
  `row-selected` class): a row click selects on every device and never deletes. Like Sessions, the
  selection lives in the URL (`?project=<path>`, via `useSearchParams` in `ProjectsPage`), so a reload
  or shared link reopens it; a `?project=` that isn't a known project (deleted, or stale) is dropped
  once the list has loaded. The page renders `ProjectDetailPanel` under the list with
  `key={project.path}`, so its time range (`TimeRangeSelector`, default "All time") resets on every
  newly selected project and a fresh query never shows the previous project's charts; selecting
  scrolls the panel into view. The panel feeds `useOverview(range, {project, groupBy: "branch"})` into
  `GroupDonutChart`, `GroupBarChart` (both `groupLabel="branch"`) and `ActivityLineChart`, or says
  no sessions were found for an empty range. A session counts under the last branch recorded in its
  transcript. The panel also owns delete: a "Delete project" button, shown only when
  `useMeta().is_local` (the API refuses remote deletes anyway), opens a `ConfirmDialog` naming the
  exact path and that it can't be undone. Confirming calls `useDeleteProject`, whose `onSuccess`
  already invalidates the `projects`, `transcripts`, and `overview` queries (the panel's
  `["overview", ...]` query key shares that prefix); on success the page clears `?project=`, and on
  failure the error stays in the dialog.
