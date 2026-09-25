## 1. API: grouping and project filter

- [x] 1.1 In `api/overview_stats.py`, turn `project_totals` into `group_totals(transcripts, key)` (top 7 + "Other", `share`/`messages_pct`/`cost_pct` unchanged), with rows keyed `group`; add a branch key mapping `""` to `"(no branch)"`. Verify with `test_overview_stats.py` cases for project grouping, branch grouping, the "(no branch)" label, and the top-7 fold.
- [x] 1.2 Add `filter_by_project(transcripts, folder)` matching `transcript.path.parent.name`. Verify with a test where two transcripts in differently-filed projects share the same `project` basename and only the requested folder's one is returned.
- [x] 1.3 Change `overview()` to take `project_folder` and `group_by` and return `groups` / `group_order` instead of `projects` / `project_order`. Verify with `test_overview_stats.py` that the empty case, the ordering, and the activity buckets are unchanged.
- [x] 1.4 In `api/server.py`, add optional `project` (path) and `group_by` (`project` | `branch`) to `GET /api/overview`: 404 unless `project` exactly matches a known project, 422 for an unknown `group_by`, folder via `claude_db.sanitize_project_path`. Verify with `test_api_data.py` via `TestClient`: scoped results, 404 unknown project, 422 bad `group_by`, two same-basename projects not merged, range still applied, and the default call unchanged apart from the key rename.
- [x] 1.5 Run `pytest` from `api/` and verify the whole suite passes.

## 2. Frontend: data layer and reusable pieces

- [ ] 2.1 Update `web/src/api/types.ts` (`OverviewResponse` uses `groups` / `group_order`, rows keyed `group`) and extend `useOverview(range, {project?, groupBy?})` in `queries.ts` with a query key that keeps the `["overview", ...]` prefix. Verify with `queries` tests that the request carries `project`/`group_by` and that `useDeleteProject` invalidation still hits it.
- [ ] 2.2 `git mv` `ProjectDonutChart` / `ProjectBarChart` to `GroupDonutChart` / `GroupBarChart` and switch them to `groups`, `groupOrder`, `groupLabel` (headings, aria labels, tooltip titles, "% of top …" caption). Update `OverviewPage` to match. Verify `npm run build` passes and Overview's wording is unchanged for `groupLabel="project"`.
- [ ] 2.3 Add `components/ConfirmDialog.tsx` + `ConfirmDialog.module.css` (native `<dialog>`, `open`/`title`/`children`/`confirmLabel`/`pending`/`error`/`onConfirm`/`onCancel`; Esc, backdrop and button dismissal blocked while `pending`). Stub `showModal`/`close` in `test-setup.ts` if jsdom lacks them. Verify with a component test: opens and closes with `open`, Cancel calls `onCancel`, buttons disabled and Esc ignored while pending, error text shown.

## 3. Frontend: Projects page

- [ ] 3.1 Reduce `ProjectsList` to a selection-only list (`selectedPath`, `onSelect`, `row-selected` class, no delete UI, selection not gated on `is_local`, row label no longer says "to delete"). Rewrite `ProjectsList` tests: a row click selects and starts no delete, on both a local and a remote `useMeta`.
- [ ] 3.2 Add `components/projects/ProjectDetailPanel.tsx`: `TimeRangeSelector` (default "All time"), `GroupDonutChart`, `GroupBarChart` and `ActivityLineChart` fed by `useOverview(range, {project, groupBy: "branch"})`, the empty-range message, and the "Delete project" button (only when `is_local`) that opens `ConfirmDialog` naming the path with the not-undoable warning. Verify with tests: charts render for a response, empty state text, delete button hidden off-machine, confirm calls the delete with the path, error stays in the modal, modal closes and `onDeleted` fires on success.
- [ ] 3.3 Wire `ProjectsPage`: `?project=<path>` via `useSearchParams`, panel rendered under the list with `key={path}` so the range resets, unknown/stale `?project=` dropped, `?project=` cleared on delete, panel scrolled into view on selection. Verify with a page test (select → panel shows; reload with `?project=` reopens it; selecting another project resets the range to All time) and manually in the browser at narrow and wide widths.

## 4. Docs and verification

- [ ] 4.1 Update `CLAUDE.md`: the Projects section (row click selects, delete is a button + modal), the `/api/overview` row in the routes table (`project`, `group_by`, `groups`), the frontend test list, and `ConfirmDialog`. Verify no remaining text describes row-click-to-delete or `project_order`.
- [ ] 4.2 Run `npm test` and `npm run build` in `web/` and `pytest` in `api/`, and verify all pass; then run `openspec validate add-project-charts --strict` and verify it passes.
- [ ] 4.3 Manually check in a real browser (per CLAUDE.md there is no E2E harness): select a project, change ranges, delete with the modal (cancel and confirm), reload with `?project=`, and view through the gateway on a phone to confirm the delete button is absent and the charts still render.
