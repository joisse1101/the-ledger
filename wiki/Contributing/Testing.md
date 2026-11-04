# Testing

This page lists how to run the Python, frontend and widget tests, and what each test file covers. It also says what is checked by hand because no automated test covers it.

## Python tests

```powershell
cd api
pip install -r requirements-dev.txt  # requirements.txt + pytest + httpx
pytest
pytest ../scripts/tests   # the docs checker and wiki builder; a plain `pytest` does not collect them
```

Run pytest from `api/`, because that is where `pyproject.toml` lives. It sets `pythonpath = ["."]` and `testpaths = ["tests"]`. The first means `from app import deps` and the root scripts import under pytest the same way they do under `python -m app` run from `api/`, which puts the cwd on `sys.path`.

The tests are one file per module under test. They are grouped below by area.

### Worktrees

- `api/tests/core/test_worktrees.py` covers the path rule.
- `api/tests/repositories/test_scanner_worktrees.py` covers the scanner.
- `test_worktree_schema.py` covers the column and the two-way reconcile.
- `test_worktree_membership.py` covers the project folder and delete.

### Settings

- `api/tests/repositories/test_settings_store.py` covers the JSON file.
- `api/tests/services/test_settings_service.py` checks that a save re-files both stores and that refusals change nothing.
- `api/tests/test_settings_routes.py` checks that the routes are local-only, even with a valid token.

An autouse fixture in `conftest.py` points `LEDGER_SETTINGS_PATH` at a `tmp_path`, so no test reads or writes the real `api/.ledger/settings.json`.

### Data layer

The files are `test_claude_db.py`, `test_claude_projects.py`, `test_claude_transcripts.py`, `test_claude_sessions.py` and `test_context.py`.

The `isolated_db` fixture in `api/tests/conftest.py` monkeypatches `paths.db_path`, `config_path` and `projects_dir` to a `tmp_path`. The suite therefore never touches the real `~/.claude.json` or `~/.claude/projects/`.

### Layering

`api/tests/test_layers.py` scans the imports under `api/app/`. It fails when a layer imports one above it, or when `repositories`, `domain`, `infra` or `services` import FastAPI. `api/tests/services/` holds the service and error-mapping tests.

### API and backend

- `test_main.py`: the FastAPI app's lifespan and refresh wiring; asserts no `CORSMiddleware` is registered.
- `test_security.py`: the auth middleware, covering local vs. remote, bearer-token matching, the CSRF header and the Host rebinding-guard.
- `test_banner.py`: address discovery, QR rendering, and the backend's now-simpler local-only startup banner.
- `test_cli.py`: `parse_settings` and `main`, covering host, port and frontend-port precedence, no token at launch, and `--lan` rejected with a message pointing at the gateway.
- `test_live_snapshot.py`: `LiveSnapshot`'s TTL coalescing and per-session failure isolation.
- `test_overview_stats.py` and `test_transcript_query.py`: the pure aggregation, filter and sort logic behind Overview and the All list.
- `test_api_data.py`: the `/api/live`, `/api/transcripts`, `/api/sessions/{id}`, `/api/projects` and `/api/overview` routes end to end via `TestClient`.
- `test_gateway_signin.py`: the sign-in and display address helpers.
- `test_pending_decisions.py`: the pending-prompt store, transcript-based clearing, and Remote mode.
- `test_relay_hook.py`: runs the real `hooks/ledgerScripts/Relay-PermissionRequest.ps1` as a subprocess against a real uvicorn server. Answers become decisions, and every no-answer path prints nothing.
- `test_hook_install.py`: the relay's `-IncludeSessionControl` and the chimes' `-IncludeChimes` install and uninstall, against a throwaway `USERPROFILE`, never the real `settings.json`.
- `test_ledger_common.py`: the shared `scripts/Ledger-Common.ps1`. It covers `.env` and port rules, the saved-port scan, prerequisite and dependency-repair planning with a fake installer, the start summary, and the stale relay-hook offer against a throwaway settings file.
- `test_widget_shortcut.py`: the widget shortcut install and uninstall into throwaway folders, with stdin closed.
- `test_install_ledger.py`: the `Install-Ledger.ps1` wizard end to end, against a throwaway `USERPROFILE`, shortcut folders and task name. It never accepts the toast hooks, which would write the real `claudecode://` handler.

The last five are skipped off Windows.

## Frontend tests

Run these from `web/`:

```powershell
npm test          # Vitest (jsdom, see web/src/test-setup.ts): api/client, api/queries, api/token,
                   # components/ButtonSelector, components/ConfirmDialog (pending blocks Esc/buttons),
                   # list/ResponsiveList, projects/ProjectsList (a row click selects, never deletes),
                   # projects/ProjectDetailPanel (charts, empty range, delete button hidden off-machine,
                   # confirm/error flow), pages/ProjectsPage (`?project=` selection, range reset),
                   # sessions/AllList (Worktree column, sort, filter), sessions/DecisionPrompt, sessions/RemoteModeControl, sessions/SessionDialog +
                   # ContextBreakdownPanel (select/replace/dismiss the pinned breakdown, estimates
                   # marked), sessions/TokensChart (tooltip markup escapes names), lib/contextBreakdown
                   # (shares of a response's own context), hooks/useDebouncedValue,
                   # hooks/useViewportClass, lib/format, lib/tokens, lib/activityTrend,
                   # components/overview/ActivityLineChart (compiles the chart spec: one shared legend)
                   # components/Nav (Settings only on the local machine), pages/SettingsPage (add, remove,
                   # refused folder, built-in row, pending state, non-local redirect)
npm run build      # tsc --noEmit, then vite build -> web/dist
```

## Widget tests

Run these from `widget/`:

```powershell
npm test          # Vitest: the loopback API client (against a stub HTTP server), the poller,
                   # the AFK flag module (throwaway folders), the process Supervisor (fake spawner:
                   # never kills what it didn't start, never touches Docker), window-state clamping/persistence, the renderer (jsdom), IPC names
npm run build     # tsc for the main process and for the renderer, then copies the static files
powershell -File tests\Test-StartWidget.ps1   # Start-Widget.ps1 against a stub backend (needs a build)
```

## Checked by hand

The always-on-top window, the tray menu and the toast-equivalent repo window are checked by hand.

There is no browser-automation/E2E harness for the React app. Responsive layout across breakpoints is verified manually, by resizing a real browser and by using a real phone through the gateway (see [Gateway](../Services/Gateway.md)).
