# Frontend: projects

This page explains how the Projects page is built: the project list, the detail panel under it, and delete. Read it before changing them.

> Requirements live in `openspec/specs/web-dashboard/spec.md`. This page describes how the code meets them, not what it must do.

## Where the code is

- `web/src/components/projects/ProjectsList.tsx` is the list.
- `web/src/components/projects/ProjectDetailPanel.tsx` is the panel.
- `web/src/pages/ProjectsPage.tsx` is the page.

## The list

`ProjectsList` renders every field from `useProjects()` through the same `ResponsiveList` the Sessions lists use. The fields are:

- Name and path.
- Trust.
- Last session.
- Version.
- Last cost.
- Last start.
- Lines +/-.
- MCP servers.

It is a selection-only list (`selectedPath`/`onSelect`, `row-selected` class). A row click selects on every device and never deletes.

### Selection in the URL

Like Sessions, the selection lives in the URL (`?project=<path>`, via `useSearchParams` in `ProjectsPage`), so a reload or shared link reopens it. A `?project=` that is not a known project (deleted, or stale) is dropped once the list has loaded.

### Source, Issues and PRs columns

`ProjectsList` also joins in `useProjectRepos()` (`GET /api/projects/repos`) by path to fill the Source, Issues and PRs columns. It is its own query so the table never waits on `git` or `gh`. Anything unknown shows `--`.

Source is a new-tab link to the repo's web page. Its click stops propagation so it does not toggle the row. On a narrow card, where the card is itself a button, it is plain text via the column's `renderCard`.

## The detail panel

The page renders `ProjectDetailPanel` under the list with `key={project.path}`. That resets its time range (`TimeRangeSelector`, default "All time") for every newly selected project, so a fresh query never shows the previous project's charts. Selecting a project scrolls the panel into view.

The panel feeds `useOverview(range, {project, groupBy: "worktree"})` into `GroupDonutChart`, `GroupBarChart` (both `groupLabel="worktree"`) and `ActivityLineChart`. For an empty range it says no sessions were found. These charts are described in [Frontend overview](Frontend-Overview.md).

A session counts under its worktree (`wt <name>`) when it ran in a Claude Code worktree, and otherwise under the last branch recorded in its transcript. The stat grid shows Branches and Worktrees counts.

The panel's "Open project" link uses the same URL as Source. It sits left of Delete and, unlike Delete, shows on every device.

## Delete

The panel owns delete. A "Delete project" button, shown only when `useMeta().is_local` (the API refuses remote deletes anyway), opens a `ConfirmDialog` naming the exact path and that it cannot be undone.

Confirming calls `useDeleteProject`. Its `onSuccess` already invalidates the `projects`, `transcripts` and `overview` queries, and the panel's `["overview", ...]` query key shares that prefix. On success the page clears `?project=`. On failure the error stays in the dialog.
