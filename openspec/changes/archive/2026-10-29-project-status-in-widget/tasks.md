## 1. Backend: widget setting

- [x] 1.1 Make `settings_store` read-modify-write per key, add the `max_projects` loader (validated by `core/widget_settings`) (default 5; missing or out-of-range reads as 5) and saver, and verify a pytest shows saving folders keeps the number and saving the number keeps the folders
- [x] 1.2 Add `settings_service.save_settings` (whole number 1 to 10, bool rejected, `InvalidInput` otherwise; validates every part before saving any) whose widget number does not call history or snapshot, and verify pytest covers 0, 11, 2.5, `True`, and that no reconcile runs
- [x] 1.3 Make both fields of `PUT /api/settings` optional, return `{worktree_folders, widget: {max_projects}}` from GET and PUT, and verify router tests cover each field alone, both, 422 on a bad value, and 403 for a non-local request with a valid token
- [x] 1.4 Update `wiki/Backend-API-Routes.md` and run `cd api; python check_docs.py` and `cd api; pytest` to verify both pass

## 2. Frontend: Settings page

- [x] 2.1 Add `widget: { max_projects }` to `Settings` in `web/src/api/types.ts` and add `useSaveWidgetMaxProjects`, which sends only the widget part and reloads nothing, and verify `npm test` for the query tests passes
- [x] 2.2 Add a "Desktop widget" section to `SettingsPage.tsx` with the projects-shown number and a Save control showing the server's message on a 422, and verify `SettingsPage.test.tsx` covers default 5, saving 3, a rejected 11, and that saving folders leaves the number
- [x] 2.3 Update the Settings page's wiki page, then verify `cd web; npm test`, `cd web; npm run build` and `python check_docs.py` pass

## 3. Widget: data

- [x] 3.1 Add `fetchProjectRepos()` and `fetchMaxProjects()` to `widget/src/main/api.ts` (loopback, no token, null on any error or malformed body, cap falls back to 5) and verify `api.test.ts` covers success, HTTP error, timeout, and a malformed body
- [x] 3.2 Add a pure function that keeps GitHub rows, names them from the path's last segment, orders by issues plus PRs with unavailable counts last and stable ties, and slices to the cap with a remainder count, and verify its unit tests cover the "+2 more" case, non-GitHub, no remote, and all-unavailable

## 4. Widget: tooltip

- [x] 4.1 Add `{kind: 'projects', rows, more}` to `TooltipContent`, render it in `tooltipView.ts` as text rows (name, source, issues, PRs; `--` when unavailable), size it by row count in `tooltipWindow.ts`, and verify `tooltipView.test.ts` covers the rows, the "+N more" line, and that no value is inserted as markup
- [x] 4.2 Add the projects controller (cache of last rows and cap, fetch at startup, every 60 seconds with `startPoller`, and on hover; loading, could-not-load and no-GitHub-projects messages; redraw only on change) and verify its tests cover instant cached hover, in-place update while open, failed read keeping rows, first-read loading, and no overlapping reads
- [x] 4.3 Share the tooltip window between the two controllers so it hides only when neither has content, and verify a test where Remote auto-shows while the Ledger is hovered

## 5. Widget: wiring

- [x] 5.1 Add the `remoteHover` channel (`ipc.ts`, preload, `WidgetBridge`, `app.ts` on the Remote button), route it to `RemoteTooltip` and route `ledgerHover` to the projects controller in `main/index.ts`, and verify the renderer and main tests cover each button reaching only its own tooltip
- [x] 5.2 Update `wiki/Widget.md`, then run `cd widget; npm test`, `cd widget; npm run build` and `cd api; python check_docs.py` to verify all pass

## 6. Verification

- [x] 6.1 Run `.\widget\Start-Widget.ps1` and verify by hand: hovering Ledger shows the GitHub projects, hovering Remote shows status or the QR, the number set in Settings changes the row count within a minute, and signing `gh` out shows `--` without breaking the list
- [x] 6.2 Run `openspec validate project-status-in-widget --strict` and verify it passes
