## 1. Scaffold `widget/`

- [x] 1.1 Create `widget/` with `package.json` (Electron, TypeScript, Vitest as dev deps), `tsconfig.json`, `src/main`, `src/preload`, `src/renderer`, `tests/`; verify `cd widget; npm ci; npm run build` succeeds and `npm test` runs (empty suite passes)
- [x] 1.2 Add `widget/node_modules` and `widget/dist` to `.gitignore`; verify `git status` stays clean after installing

## 2. Data flow (main process)

- [x] 2.0 Add `git_branch` to `/api/live` items (`claude_db.git_branches`, `LiveSnapshot`) and document it in `wiki/Backend-API-Routes.md`; verify `cd api; pytest` passes with new tests for present, missing and failing lookups

- [x] 2.1 Implement the `/api/live` poller (loopback `Host`, 3 s timeout, ~2 s interval) returning `{state: 'online', sessions}` or `{state: 'offline'}`; verify unit tests with a stub server cover success, non-200, connection refused and timeout, and that an offline result carries no stale rows
- [x] 2.2 Implement the `open-repo` caller (`POST`, `X-Requested-With: ledger`) distinguishing 404 (session ended) from other failures; verify unit tests for 200, 404 and network error
- [x] 2.3 Implement process ownership: probe `/api/meta`, spawn backend hidden if absent, track only children it spawned, tree-kill them on quit; verify tests with a fake spawner show an already-running backend is never killed and a spawned one is
- [x] 2.4 Implement "Open Ledger": reuse a running frontend, otherwise build if `web/dist` is missing, spawn `vite preview` hidden, wait for the port, open the browser; verify tests show no gateway/docker command is ever issued and no second frontend starts when one is up

## 3. Window, tray and renderer

- [x] 3.1 Create the frameless always-on-top window with `contextIsolation`, `sandbox`, no `nodeIntegration`, a strict CSP and a narrow preload API; verify by launching it and checking it stays above another window and that `window.require`/`process` are undefined in the renderer
- [x] 3.2 Add single-instance lock (second launch focuses the first), persisted bounds clamped to a visible display, and the collapse/expand pill; verify unit tests for bounds clamping and persistence round trip, and manually that a second launch creates no second window
- [x] 3.3 Render rows: project and branch, `context.label` verbatim (or `--` when `context` is null), `pending` badge from `pending_decision` with no prompt text or controls, and the "no live sessions" and offline states; verify renderer tests for each state and that no percentage or limit text can appear
- [x] 3.4 Wire row click to `open-repo` with a transient "session ended" note on 404 and an immediate refresh; verify a test with a stubbed API and a manual check that a toast-equivalent repo window opens
- [ ] 3.5 Add the tray menu (Open Ledger, Start backend, Show/Hide, Quit); verify Quit stops only widget-started processes (task 2.3 tests plus a manual check)

## 4. Startup scripts

- [x] 4.1 Write `Start-Widget.ps1` (resolve ports with `Start-Ledger.ps1`'s precedence into env vars, `npm ci` if `widget/node_modules` is missing, build if `dist` is stale or missing, launch Electron) plus a silent `.vbs` launcher; verify a cold start leaves the backend and widget running, no console window, and no frontend or Docker container
- [ ] 4.2 Write `Install-WidgetShortcut.ps1` (`-Desktop`, `-Startup`) and `Uninstall-WidgetShortcut.ps1`; verify the shortcuts are created and removed, the desktop shortcut still works after the Startup one is removed, and a sign-out/sign-in with `-Startup` brings up the widget
- [x] 4.3 Add a PowerShell-level check (Pester-free, script-run like the other hook tests) that `Start-Widget.ps1 -Help` works and that a second run with the backend already up starts no second backend; verify it passes

## 5. Docs and verification

- [x] 5.1 Update `CLAUDE.md` (six folders, routing row, commands), `wiki/Repository-Layout.md` and `wiki/Coding-Standards.md` folder counts; verify `cd api; python check_docs.py` passes
- [x] 5.2 Add `wiki/Widget.md` (how it works, ports, startup, ownership rules; link to the spec, don't restate it), link it from `wiki/Home.md` and `wiki/_Sidebar.md`, and add `widget` tests to `wiki/Testing.md`; verify `python check_docs.py` passes and the Widget page is not an orphan
- [ ] 5.3 End to end: with the backend off, run the desktop shortcut, start a Claude Code session, confirm the row, its context figure matching the Live table, the `pending` badge during a permission prompt, click-to-open, Open Ledger starting only the frontend, and Quit; record the result in the PR description
- [x] 5.4 Run `cd api; pytest`, `cd web; npm test`, `cd web; npm run build` and `cd widget; npm test; npm run build`; verify all pass with no regressions
