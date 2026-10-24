## 1. Configurable worktree path rule (core)

- [x] 1.1 In `api/app/core/worktrees.py`, add `BUILT_IN_FOLDER`, a `folder` field on `Worktree`, and `parse_worktree(cwd, folders)` building one longest-first alternation from the built-in plus the given folders (design: "The folder list is passed into `parse_worktree`"); extend `api/tests/core/test_worktrees.py` with a `.trees` session, a nested folder (`tools/wt`), a session `cd`'d deeper, a folder not in the list (`None`), `wt` vs `wt/inner` picking the longer, and the existing `.claude/worktrees` cases still passing with no folders; verify `pytest tests/core/test_worktrees.py` passes
- [x] 1.2 Add `normalize_folder(raw)` beside it: backslashes to `/`, trim slashes, reject empty, absolute (drive letter, leading `/` or `\`), and `.`/`..` segments with a reason; verify tests for `tools\wt\` -> `tools/wt`, `../shared`, `C:/trees`, `/trees`, `a/./b`, and blank input

## 2. Settings store and the scans that use it (repositories)

- [x] 2.1 Add `api/app/repositories/settings_store.py` reading and writing `api/.ledger/settings.json` (override `LEDGER_SETTINGS_PATH`), user folders only, atomic write, missing or invalid file = no folders (design: "Settings live in a small JSON store"); verify tests with `tmp_path` for round-trip, missing file, and corrupt JSON
- [x] 2.2 Load the list at the start of each scan in `repositories/db/scanner.py` and pass it to `parse_worktree`; make `paths.project_folder` strip the suffix of whichever folder matched; verify `tests/repositories/test_scanner_worktrees.py` and `test_worktree_membership.py` gain `.trees` cases (session attributed to its repo, project delete removes `.trees` worktree sessions) and still pass with no settings file
- [ ] 2.3 Turn `history.correct_worktree_rows` into the two-way reconcile from the design's table, using the stored list; verify tests: a pruned `.trees` row gains its worktree when `.trees` is listed, loses it (project = worktree name) when removed, `.claude/worktrees` rows never revert, and a second pass changes nothing
- [x] 2.4 Verify `pytest tests/test_layers.py tests/test_backup_history.py` pass and that `backup_history.py` attributes a `.trees` session when the settings file lists `.trees`
- [ ] 2.5 Update `wiki/Backend-Data-Layer.md` and `wiki/Backend-History-Store.md` for configured folders and the two-way reconcile; verify `python check_docs.py` passes

## 3. Settings API (services, routers)

- [ ] 3.1 Add `services/settings_service.py`: `get()` returns built-in plus user folders; `save(folders)` normalizes, rejects invalid or duplicate folders with the reason, writes, reconciles history, then rescans (design: "Saving runs validate, write, reconcile, rescan in order"); verify service tests that a save moves a `.trees` session under its repo and a later removal moves it back, without a restart
- [ ] 3.2 Add `routers/settings.py` with `GET` and `PUT /api/settings`, both 403 unless `is_local(request)`, and register it in `main.py`; verify API tests: local read and save succeed without a token, a non-local request with a valid token is refused for both and the file is unchanged, and an invalid folder returns 400 with its reason
- [ ] 3.3 Document the routes in `wiki/Backend-API-Routes.md` and the local-only rule in `wiki/Backend-Security.md`; verify `python check_docs.py` passes

## 4. Settings page (web)

- [ ] 4.1 Add the settings types, `useSettings` query and `useSaveSettings` mutation in `web/src/api/`, invalidating the sessions, projects, overview and options queries on success; verify `queries.test.tsx` covers the `PUT` body and the invalidation
- [ ] 4.2 Add a `localOnly` Settings entry to `Nav.tsx` (filtered on `useMeta().data?.is_local`) with an icon, and the `settings` route in `App.tsx`; verify `Nav.test.tsx` shows the entry for a local meta and hides it for a non-local one, with or without Remote mode
- [ ] 4.3 Add `pages/SettingsPage.tsx`: redirect non-local devices to `/`; list `.claude/worktrees` as built in with no remove control; user folders each with Remove; an Add input that saves at once, shows a pending state, and shows server validation errors inline; verify `SettingsPage.test.tsx` covers add, remove, a rejected folder, the built-in row, and the non-local redirect
- [ ] 4.4 Document the page in `wiki/Frontend-Shell-And-Theme.md` (nav entry, local-only) and link it from `wiki/Home.md`; verify `npm test`, `npm run build` and `python check_docs.py` pass

## 5. End-to-end check

- [ ] 5.1 With `.\Start-Ledger.ps1` running, open the dashboard on `localhost`, add `.trees`, and confirm this repo's `.trees/config-worktree-path` sessions appear under `the-ledger` with worktree `config-worktree-path` on Overview, Projects and Manage Sessions; remove it and confirm they return to a `config-worktree-path` project; open through the gateway from another device and confirm there is no Settings entry and `/api/settings` is refused

## Workflow follow-up

- Archive the change after review, updating any wiki page the implementation changed beyond the ones above.
