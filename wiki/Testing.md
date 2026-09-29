# Testing

```powershell
cd api
pip install -r requirements-dev.txt  # requirements.txt + pytest + httpx
pytest
```

Run pytest from `api/` — that's where `pyproject.toml` lives. It sets `pythonpath = ["."]` (so bare
imports like `import server`/`import claude_db` work under pytest the same way running
`api/server.py` directly puts its own directory on `sys.path` at runtime) and `testpaths = ["tests"]`.

Python tests, one file per module under test:
- Data layer: `test_claude_db.py`, `test_claude_projects.py`, `test_claude_transcripts.py`,
  `test_claude_sessions.py`, `test_claude_context.py`. `api/tests/conftest.py`'s `isolated_db` fixture
  monkeypatches `claude_db.db_path`/`config_path`/`projects_dir` to a `tmp_path`, so the suite never
  touches the real `~/.claude.json` or `~/.claude/projects/`.
- API/backend: `test_server.py` (the FastAPI app's lifespan/refresh wiring, asserts no
  `CORSMiddleware` is registered), `test_security.py` (the auth middleware — local vs. remote,
  bearer-token matching, CSRF header, Host rebinding-guard), `test_banner.py` (address discovery,
  QR rendering, the backend's now-simpler local-only startup banner), `test_cli.py`
  (`parse_settings`/`main` — host/port/frontend-port precedence, token provisioning on launch,
  `--lan` rejected with a message pointing at the gateway),
  `test_live_snapshot.py` (`LiveSnapshot`'s TTL coalescing and per-session failure isolation),
  `test_overview_stats.py` and `test_transcript_query.py` (the pure aggregation/filter/sort logic
  behind Overview and the All list), `test_api_data.py` (the `/api/live`, `/api/transcripts`,
  `/api/sessions/{id}`, `/api/projects`, `/api/overview` routes end to end via `TestClient`),
  `test_gateway_signin.py` (`gateway_signin.py`'s sign-in banner/QR building and its own CLI),
  `test_pending_decisions.py` (the pending-prompt store, transcript-based clearing, Remote mode),
  `test_relay_hook.py` (runs the real `hooks/ledgerScripts/Relay-PermissionRequest.ps1` as a subprocess
  against a real uvicorn server: answers become decisions, and every no-answer path prints nothing),
  `test_hook_install.py` (the relay's `-IncludeSessionControl` install/uninstall against a throwaway
  `USERPROFILE`, never the real `settings.json`). The last two are skipped off Windows.

Frontend (`cd web`):

```powershell
npm test          # Vitest (jsdom, see web/src/test-setup.ts): api/client, api/queries, api/token,
                   # components/ButtonSelector, components/ConfirmDialog (pending blocks Esc/buttons),
                   # list/ResponsiveList, projects/ProjectsList (a row click selects, never deletes),
                   # projects/ProjectDetailPanel (charts, empty range, delete button hidden off-machine,
                   # confirm/error flow), pages/ProjectsPage (`?project=` selection, range reset),
                   # sessions/DecisionPrompt, sessions/RemoteModeControl, hooks/useDebouncedValue,
                   # hooks/useViewportClass, lib/format, lib/tokens, lib/activityTrend,
                   # components/overview/ActivityLineChart (compiles the chart spec: one shared legend)
npm run build      # tsc --noEmit, then vite build -> web/dist
```

There is no browser-automation/E2E harness for the React app; responsive layout across breakpoints
is verified manually (resizing a real browser, and a real phone through the gateway — see [Gateway](Gateway.md)).
