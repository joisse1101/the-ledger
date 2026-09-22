# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A dashboard for viewing your local Claude Code sessions and projects: Overview, Sessions (Live +
All), Projects. The repo is **mid-migration** between two front ends that read the same on-disk
Claude Code data:

- `streamlit_app/` — the original Streamlit app. Complete: all three pages, live polling, search/
  filter/sort, session-detail dialogs, delete flows.
- `api/` (FastAPI backend) + `web/` (React + Vite frontend) — the replacement, built to also allow
  read access from other devices on the network (a phone) behind a shared access token, which
  Streamlit has no way to do safely. As of this writing it covers Overview and Sessions (Live, All,
  the session-detail view, and delete) with responsiveness down to phone widths; the Projects page
  (`web/src/pages/ProjectsPage.tsx`) is still a stub (just a heading). Streamlit has not been
  removed — cutover is the last step of the migration, once the React app has full parity.

The migration's rationale, decisions, and status are recorded in
`openspec/changes/migrate-to-react-lan-access/` (`proposal.md` for why/what, `design.md` for the
decisions, `tasks.md` for the checklist) — **check `tasks.md` before assuming either UI's state**,
rather than inferring it from this file, since it's the thing that's kept current task-by-task as
the migration proceeds. Don't assume Streamlit is gone or that the React app is at parity without
checking there and in the actual code.

Both UIs currently read/write the *same* SQLite snapshot at `.streamlit/ledger.db` (the DB path
move to `.ledger/` is one of the not-yet-done cutover tasks) and the same `~/.claude.json` /
`~/.claude/projects/*/*.jsonl` on disk.

## Setup & Run

Create/activate the venv and install Python dependencies (covers both UIs — `fastapi`, `uvicorn`,
`qrcode` are additive to the original `streamlit`/`pandas`):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

A `.venv` already exists at the repo root with dependencies installed — activate it
(`.venv\Scripts\Activate.ps1`, or invoke `.venv\Scripts\python.exe` / `.venv\Scripts\pytest.exe`
directly) rather than searching for or recreating one.

**Streamlit app** (run from the repo root, not from inside `streamlit_app/`):

```powershell
streamlit run streamlit_app/app.py
```

Opens at http://localhost:8501. `.streamlit/config.toml` sets `runOnSave = true`, so it auto-reloads
on file changes while `streamlit run` is active.

**React + FastAPI app** — needs Node.js in addition to the Python setup above. Run the Python
commands from the repo root, not from inside `api/`.

Development (hot-reloading frontend, two terminals):

```powershell
python api/server.py            # the API, on http://localhost:8501
cd web; npm install; npm run dev  # the UI, on http://localhost:5173, proxies /api to 8501
```

Built (one server, one port — also what's needed to reach the app from another device):

```powershell
cd web; npm ci; npm run build; cd ..
python api/server.py
```

Opens at http://localhost:8501. Pass `--lan` to bind every network interface instead of just this
machine (`python api/server.py --lan`); the server then prints a URL, a QR code, and a one-time
access token per discovered address for a phone to sign in with (see `api/security.py` /
`api/banner.py` below). `--host`/`--port` (or `LEDGER_HOST`/`LEDGER_PORT`) override the address/port.
Both apps default to port 8501 — run only one at a time unless you also change one's port.

## Testing

```powershell
pip install -r requirements-dev.txt  # requirements.txt + pytest + httpx
pytest
```

`pyproject.toml` sets `pythonpath = [".", "streamlit_app", "api"]` (so bare imports like `import
app`, `import server`, `import views.overview` work under pytest the same way each entry point's
own `sys.path` bootstrap makes them work at runtime — see `streamlit_app/app.py` and
`api/server.py`) and `testpaths = ["tests"]`.

Python tests, one file per module under test:
- Shared data layer: `test_claude_db.py`, `test_claude_projects.py`, `test_claude_transcripts.py`,
  `test_claude_sessions.py`, `test_claude_context.py`. `tests/conftest.py`'s `isolated_db` fixture
  monkeypatches `claude_db.db_path`/`config_path`/`projects_dir` to a `tmp_path`, so the suite never
  touches the real `~/.claude.json` or `~/.claude/projects/`.
- Streamlit: `test_app.py` (the `_auto_refresh_due` gate logic), `test_overview.py` (the pure
  aggregation functions in `views/overview.py`), `test_views.py` (`_sessions_dataframe`/
  `_transcripts_dataframe`/`_projects_dataframe` and the filter/sort helpers). Streamlit *rendering*
  itself (`render_*` functions that call `st.*` widgets) isn't covered.
- API/backend: `test_server.py` (the FastAPI app's lifespan/refresh wiring), `test_security.py` (the
  auth middleware — local vs. remote, token matching, sign-in redirect, CSRF header, Host
  rebinding-guard), `test_banner.py` (address discovery, QR rendering, banner text), `test_cli.py`
  (`parse_settings`/`main` — host/port precedence, token provisioning on launch), `test_frontend.py`
  (serving `web/dist`, SPA fallback, the "not built yet" response), `test_live_snapshot.py`
  (`LiveSnapshot`'s TTL coalescing and per-session failure isolation), `test_overview_stats.py` and
  `test_transcript_query.py` (the pure logic ported out of `views/overview.py`/`views/sessions_data.py`
  into `overview_stats.py`/`transcript_query.py` — kept in step with `test_overview.py`/`test_views.py`
  until Streamlit's versions are retired), `test_api_data.py` (the `/api/live`, `/api/transcripts`,
  `/api/sessions/{id}`, `/api/projects`, `/api/overview` routes end to end via `TestClient`).

Frontend (`cd web`):

```powershell
npm test          # Vitest: client.test.ts, queries.test.tsx, useDebouncedValue/useViewportClass
                   # tests, format.test.ts, tokens.test.ts (jsdom, see web/src/test-setup.ts)
npm run build      # tsc --noEmit, then vite build -> web/dist
```

There is no browser-automation/E2E harness for the React app; responsive layout across breakpoints
is verified manually (resizing a real browser, and a real phone over `--lan`) per
`openspec/changes/migrate-to-react-lan-access/tasks.md`'s groups 9–10.

## Architecture

### Shared data layer (repo root)

These modules are Streamlit-free plain Python, read by both `streamlit_app/` and `api/`, and
deliberately stay at the repo root rather than moving into either folder (or a new shared package —
considered and rejected) since that would touch every import on both sides for no real benefit.

- `claude_db.py` is the single SQLite-backed store that `claude_projects.py` and
  `claude_transcripts.py` both read from, rather than each independently scanning and mtime-caching
  its own file(s) on disk as they used to. All of that disk-reading — `~/.claude.json` and
  `~/.claude/projects/*/*.jsonl` parsing, the `_MODEL_PRICING` table, `sanitize_project_path()`, etc.
  — lives here. `refresh()` rescans both sources, resolves each transcript's `project` from the
  just-scanned project list (matching the transcript's on-disk parent folder against
  `sanitize_project_path()`), replaces the `projects`/`transcripts` tables' contents in one pass, and
  stamps a `meta.refreshed_at` timestamp; `refreshed_at()` reads that timestamp back. This is the
  *only* place disk gets rescanned — triggered explicitly (Streamlit's "⟳" button, or `POST
  /api/refresh`), plus once automatically via `startup()` on process start, plus a periodic
  background pass (a 10-minute Streamlit fragment on that side, a 10-minute `asyncio` loop task on
  the API side — see `api/server.py`). `startup()` treats the database as a pure derived cache: it
  deletes any leftover db file from a previous run, calls `refresh()` to rebuild it from disk, and
  registers an `atexit` handler to delete it again on exit (best-effort). `db_path()` currently
  returns `.streamlit/ledger.db` for **both** UIs (the move to `.ledger/ledger.db` is a not-yet-done
  cutover task — see `openspec/changes/migrate-to-react-lan-access/tasks.md` §10.2); don't assume the
  path from that design doc's prose without checking the function.
  `_connect()` sets `PRAGMA journal_mode=WAL` and a busy timeout — added for the FastAPI server's
  concurrent-request model (multiple browsers/phones reading while a background `refresh()` writes),
  not needed by Streamlit's single-script-thread model, but it lives here since both read the same
  file; `startup()`/its `atexit` hook also clean up the `-wal`/`-shm` files. `load_projects()` /
  `load_transcripts()` just `SELECT * ... ORDER BY` these tables and build dataclasses from the rows
  — cheap enough to call fresh on every request/rerun with no caching of their own. `delete_project()`
  / `delete_project_transcripts()` / `delete_transcript()` each mutate the real on-disk source first,
  then delete just the matching row(s) from SQLite by key, rather than calling `refresh()` again — a
  full rescan isn't needed since the key just removed from disk is exactly the key to remove from the
  db.
- `claude_projects.py` holds the `ClaudeProject` dataclass and query/delete functions for Claude
  Code's project data (originally `~/.claude.json`'s top-level `projects` map — one entry per
  directory Claude Code has been run/trusted in, reflecting only that project's *last* session:
  trust status, last session ID, CLI version, cost, start time, lines added/removed, any
  project-scoped MCP servers). `delete_project(project_path)` edits `~/.claude.json` directly (the
  real source of truth) then removes the matching row from SQLite via `claude_db.delete_project_row()`.
- `claude_transcripts.py` holds the `ClaudeTranscript` dataclass and query/delete functions for
  session transcript data (originally parsed line-by-line from
  `~/.claude/projects/<sanitized-cwd>/<session-id>.jsonl` — every session that has ever run,
  including exited ones; the parsing itself lives in `claude_db.py`'s `refresh()`). That parsing
  derives `started_at`/`updated_at` (min/max line timestamp), `message_count` (non-meta `user`/
  `assistant` lines), `context` (the same latest-real-main-thread-turn figure `claude_context.py`
  shows live, via `claude_db._context_tokens`), `cost` (per-turn `message.usage` priced via
  `_MODEL_PRICING`, counted once per unique `message.id`; an *estimate* — unrecognized models are
  silently skipped), and `project` (matching the on-disk parent folder against each project's
  `sanitize_project_path()`, falling back to a cwd/folder-derived guess). `delete_project_transcripts(cwd)`
  and `delete_transcript(session_id)` look up the affected path(s) via `claude_db`, remove the real
  file(s), then delete just those rows from SQLite.
- `claude_sessions.py` parses Claude Code's live session registry at `~/.claude/sessions/<pid>.json`
  (one file per process) directly from disk on every call — unlike projects/transcripts this isn't
  routed through `claude_db.py`, since the Live views poll it every ~2s and a snapshot refreshed only
  on demand would defeat that. `load_sessions()` returns `ClaudeSession` dataclasses sorted by
  `updated_at` descending, with its own module-level cache keyed by each file's mtime. Dead PIDs'
  files may linger, so entries aren't guaranteed to reflect live processes. Each session's `project`
  is resolved by looking up its `session_id` in `claude_transcripts.load_transcripts()` and reusing
  that transcript's `project`, falling back to a `cwd`-derived guess for a brand-new session with
  nothing written to disk yet.
- `claude_context.py` reads a live session's token usage straight from its transcript, outside
  `claude_db.py`/SQLite for the same reason `claude_sessions.py` is. The transcript is located from
  the registry's `cwd` and session ID, falling back to one memoized `*/<session-id>.jsonl` glob.
  **Context** is the latest real main-thread assistant turn's `input + cache_read + cache_creation`
  tokens ("real" = not `isSidechain`, model not `<synthetic>`, non-zero usage, de-duplicated by
  `message.id`). `live_context()` tail-reads backwards from EOF in a doubling window, memoized by
  `(path, size, mtime_ns)`; returns a `LiveContext(size, growth, history)` or `None`, never raises.
  `format_context()` renders `394k ▲ +2.1k ▁▂▃…` (`humanise_tokens` for sizes, one-decimal `k` for
  growth, a block-glyph sparkline scaled 0→window-max). The API's `live_snapshot.py` calls this same
  function so the Live list's `label` text is identical between the two UIs. For the detail dialog/
  view, `load_detail()` fully parses the transcript on demand into per-turn records plus
  `compact_boundary` compactions; growth attribution credits each turn's context delta to the first
  tool called in the previous turn (or "prompt / text"), since the latest compaction, with
  `first-turn context + attributed growth == current context` holding exactly. Main thread only —
  subagent transcripts are ignored.

### `streamlit_app/` — the Streamlit UI

`streamlit_app/app.py` is the entry point. Because it lives one directory below the repo root but
the shared data-layer modules live at the root, it inserts the repo root onto `sys.path` itself
before importing them (`streamlit run` only puts the script's own directory on `sys.path`). It seeds
`claude_db`'s SQLite snapshot on the very first run (`claude_db.startup()`) and drives a top nav bar
(`st.container(horizontal=True, vertical_alignment="center")`): the "**The Ledger**" brand, three
`st.button`s — "Overview", "Manage Sessions", "Manage Projects" (highlighted `type="primary"` for
`st.session_state.page`, set via each button's `on_click` rather than its return value so the
highlight reflects a click immediately instead of lagging one rerun behind), an empty `st.caption("")`
used purely as a flexible spacer, a "Dark mode" `st.toggle`, and a "⟳" refresh button + "Last
refreshed: HH:MM:SS"/"Never refreshed" caption (the caption reads `claude_db.refreshed_at()` *after*
that click is handled via `st.rerun()`, so a click's new timestamp shows in the same script run).
Dark mode flips `streamlit.config.set_option("theme.base", ...)` — undocumented and process-wide
(re-themes every connected tab) — persisted to a gitignored `.streamlit/theme_pref.json` so it
survives restarts without repo churn. `_auto_refresh_data()`, an invisible
`@st.fragment(run_every="10m")` called once per script run, gates a background `claude_db.refresh()`
+ `st.rerun()` behind `_auto_refresh_due(last, now)` (a plain, unit-tested function) so most of its
per-rerun calls are no-ops and only one call per 10-minute interval does the refresh; this only runs
while a browser tab is open. Page dispatch (`Overview`/`Sessions`/`Projects`) is a plain `if/elif` on
`st.session_state.page`.

`streamlit_app/views/` holds each page's render functions (kept out of `app.py` to limit it to nav/
theming/dispatch; named `views/` rather than `pages/` to avoid colliding with Streamlit's own
auto-detected multipage-app convention, which this app doesn't use):

- `views/overview.py` (`render_overview_page`) opens with an `st.segmented_control` time-range
  filter (`_TIME_RANGES`: All time/Today/Yesterday/Past week/Past month/Past quarter/Past year,
  bucketed by *local calendar date*, not a rolling window) that scopes everything below it. A
  two-column row — a donut chart of session counts by project on the left, an `st.metric` KPI grid
  on the right (counts/duration/cost, with the longest/shortest/most-expensive/cheapest figures
  carrying a `help=` tooltip naming their project/session) — followed by two full-width grouped-bar
  charts ("Messages & Cost by Project", "Activity by Hour of Day"), each measure normalized to % of
  its own peak so two differently-scaled measures can share one axis instead of a dual-axis chart.
  All three project-based charts read from one `_project_totals_dataframe()` call (top-7 + "Other",
  ranked by session count) so a project's color never shifts between charts; colors come from a
  fixed-order categorical palette (`_CATEGORICAL_LIGHT`/`_CATEGORICAL_DARK`) chosen per
  `theme.base`, exposed via `_theme_colors()` (also imported by `views/sessions_context.py` for its
  chart, and ported to TypeScript CSS variables for the React app — see `web/` below). This module
  is also where `api/overview_stats.py` was ported *from*: keep the two in step if you touch either
  (`tests/test_overview.py` and `tests/test_overview_stats.py` carry equivalent cases).
- `views/projects.py` (`render_projects_table`) is a plain, non-fragment render (no polling, no
  caching of its own). An "Edit mode" toggle switches a plain `st.dataframe` for one with
  `on_select="rerun", selection_mode="single-row"` (key `"projects_table"`); selecting a row surfaces
  a delete button which sets `confirm_delete_project` to show an inline confirm/cancel warning.
  Confirming calls `_clear_project()` (`delete_project` + `delete_project_transcripts`, each already
  updating the SQLite snapshot directly) then pops `"projects_table"` from session state (`.pop()`,
  not direct assignment, to avoid `StreamlitWidgetAlreadyInstantiatedError`).
- `views/sessions.py` (`render_sessions_page`) is now just page composition — a header plus
  `render_sessions_table()` (Live) and `render_transcripts_table()` (All); the actual table logic
  lives in the two modules below.
- `views/sessions_live.py` (`render_sessions_table`) is an `@st.fragment(run_every="2s")`: an
  "Auto-refresh" toggle + "Last refreshed" caption row, then the Live table itself, rendered via the
  shared row components in `sessions_table.py`. When auto-refresh is off the fragment still ticks on
  schedule but redisplays the cached `st.session_state.sessions_df` instead of re-reading sessions.
  Clicking a row opens the "Session context" dialog (`sessions_context.py`'s `_open_context_dialog`).
- `views/sessions_transcripts.py` (`render_transcripts_table`) is a plain render (search box +
  Project/Version/Branch `st.multiselect` filters + a sortable header, all backed by
  `sessions_data.py`) for the "All" table — every session transcript ever recorded, not just live
  ones. Clicking a row opens the "Session details" dialog (`_open_transcript_dialog`), which is also
  where deleting that transcript now lives (see `sessions_context.py` below) — there is no longer a
  separate Edit-mode/multi-row-select delete flow on this table itself.
- `views/sessions_table.py` holds the presentation pieces shared by both tables: `_ROW_CSS` (a CSS
  hack that lays a row's cells out with plain `st.columns` and overlays an invisible full-row
  `st.button` on top via `[class*="st-key-sessrow-"]`/absolute positioning, so the whole row is
  clickable without Streamlit's `st.dataframe` row-selection UI), `_render_table_row` /
  `_render_table_header` / `_render_sortable_table_header` (the sortable variant toggles
  `st.session_state[sort_state_key]` and reruns), `_format_context` (the All table's numeric,
  `humanise_tokens`-formatted Context column; `"--"` for a pandas `NaN`), and `_tooltip_text` (the
  hover tooltip on a row's invisible button, previewing the title/session ID and last
  message/first prompt).
- `views/sessions_data.py` builds the two tables' `pandas.DataFrame`s (`_sessions_dataframe`,
  `_transcripts_dataframe`, each row keyed by the columns the two dialogs and tables above expect)
  and the All table's filter/sort logic (`_filter_transcripts_dataframe`: literal
  case-insensitive substring match over Session ID/Last Message/First Prompt, AND-combined with
  Project/Version/Branch `isin` filters; `_sort_transcripts_dataframe`: a stable `mergesort` with
  missing values pushed last either direction) and `_categorical_options` (distinct non-blank
  values for a filter's choices). `_context_cell` wraps `claude_context.live_context` so one
  unreadable transcript renders `"--"` instead of sinking the whole Live table. This is also where
  `api/transcript_query.py` was ported *from* — keep the two in step (`tests/test_views.py` and
  `tests/test_transcript_query.py` carry equivalent cases).
- `views/sessions_context.py` renders the two session-detail `st.dialog`s, keyed off separate
  session-state entries so only one can be open per script run and each opener clears the other's:
  `_render_context_dialog` ("Session context", opened from a Live row — token/cache history and
  attribution only) and `_render_transcript_dialog` ("Session details", opened from an All row — the
  same detail plus a recap block of title/last-message-or-first-prompt/started/updated/messages/
  cost, and `_render_delete_controls`: a "🗑️ Delete this session" button → inline confirm/cancel
  warning → `delete_transcript` + dialog dismiss, disabled with a caption when the session is still
  live). The shared detail body (`_render_detail`) is a stacked-bar Vega-Lite chart of tokens per
  response (`_render_history_chart`: Cache read/Cache written/New, with a ▼ marker on cache-miss
  responses and a dashed rule on the first response after a compaction, colored via
  `views/overview.py`'s `_theme_colors()`), an "All responses" `st.dataframe` in an expander, and
  "What filled the context" (by-tool growth table plus largest single increases). This is the module
  the React app's `SessionDialog`/`TokensChart` were ported *from* — both sides' chart specs and
  copy should read the same.
- `views/utils.py` holds `format_date`, a tiny shared cell-formatting helper (blank/NaN → `"--"`,
  `datetime`/`Timestamp` → `"%Y-%m-%d %H:%M:%S"`).

### `api/` — the FastAPI backend

`api/server.py` is both the ASGI app and the CLI (`python server.py [--lan] [--host] [--port]`,
env `LEDGER_HOST`/`LEDGER_PORT`; default host `127.0.0.1` port `8501`, `--lan` binds `0.0.0.0`). Like
`streamlit_app/app.py`, it inserts the repo root onto `sys.path` before importing the root-level
modules (it lives one level below the root too, alongside its own supporting modules). Its
`lifespan` calls `claude_db.startup()` in a worker thread on start and runs a 10-minute
`refresh_loop()` for as long as the process is up, both funneled through a process-wide
`_refresh_lock` shared with `POST /api/refresh` so a scan (which can take seconds on a big history)
is never triggered twice concurrently. Routes:

| Endpoint | Notes |
|---|---|
| `GET /api/meta` | `{refreshed_at}` |
| `POST /api/refresh` | Forces a `locked_refresh()`, returns the new `refreshed_at` |
| `GET /api/live` | `{sessions: [...]}` from the shared `LiveSnapshot` (see `live_snapshot.py`) |
| `GET /api/transcripts` | `q`, `project[]`, `version[]`, `branch[]`, `sort`, `dir`, `limit`, `offset` → paged items + `total` + filter `options`, via `transcript_query.py`; each item's `live` flag comes from the same `LiveSnapshot`'s live-ID set |
| `GET /api/sessions/{id}` | Recap + `SessionDetail` JSON, or `readable: false`. `id` is validated against `^[A-Za-z0-9-]{1,64}$` at the route; `cwd` is resolved server-side from the live registry or the transcripts snapshot, **never** from a request parameter |
| `DELETE /api/sessions/{id}` | 409 if `live.is_live_now(id)` (a *fresh* registry read, not the ≤1s snapshot — a session that just started can't be deleted on stale data), 404 if unknown, else `claude_transcripts.delete_transcript` under the refresh lock |
| `GET /api/projects` | `{projects: [...]}` |
| `DELETE /api/projects?path=` | 404 unless `path` exactly matches a known project; then `delete_project` + `delete_project_transcripts` |
| `GET /api/overview?range=` | 422 for an unknown range label; otherwise `overview_stats.overview()`'s payload |

It also serves the built frontend: `web/dist` assets get long-cache/immutable headers when under
`assets/` (Vite's content-hashed filenames), everything else no-cache; any non-`/api` path with no
file extension falls back to `index.html` (SPA routing); if `web/dist` hasn't been built yet, page
requests get `banner.NOT_BUILT_MESSAGE` (503) instead of failing, while `/api/*` still works. `GZipMiddleware`
and `SecurityMiddleware` (outermost, so nothing else runs for a refused request) wrap every route.
Windows MIME-type registry quirks are worked around explicitly (`.js`/`.mjs` etc. get their type
forced, since Windows can otherwise answer `text/plain` for `.js`, which browsers refuse to run as a
module script).

- `api/security.py` — one ASGI middleware gating every request (see also `design.md`'s "Auth" decision).
  A request is **local** only when `request.client.host` is loopback (`127.0.0.1`/`::1`/
  `::ffff:127.0.0.1`) *and* carries none of `Forwarded`/`X-Forwarded-For`/`X-Real-IP` (so a tunnel or
  reverse proxy on the same machine is treated as remote, not silently trusted); local requests must
  still present `Host: localhost`/`127.0.0.1`/`[::1]` (any port) or get a 403 — this stops a public DNS
  name that resolves to 127.0.0.1 from reaching the app unauthenticated. Non-local requests need the
  access token via `?token=` (GET/HEAD only — a valid one triggers a 303 redirect to the same URL
  with `token` stripped and sets an `HttpOnly`/`SameSite=Lax`/one-year cookie, so the token never sits
  in browser history), the `ledger_token` cookie, or an `Authorization: Bearer` header; comparisons
  use `hmac.compare_digest`. Every non-GET request additionally needs an `X-Requested-With: ledger`
  header — a page on another site can't add a custom header without triggering a CORS preflight,
  which this app never grants (no CORS middleware at all), so that header is what stops a blind
  cross-site `POST`/`DELETE`. `provision_token()` is `LEDGER_TOKEN` if set, else `.ledger/token`
  (created with `secrets.token_urlsafe(32)` on first `--lan` run, mode `0o600`).
- `api/banner.py` — what the server prints at startup: the local URL always; with `--lan`,
  `discover_ipv4()` (a UDP-connect trick to find the outbound interface, plus hostname resolution,
  filtered by `usable_ipv4` to drop loopback/link-local/unspecified addresses) drives one
  `http://<ip>:<port>/?token=<token>` line per address plus an ASCII QR (`render_qr`, via `qrcode`;
  `None` if the package or the terminal's encoding can't render it) for the first address, and a
  plain-HTTP/trusted-networks warning. `NOT_BUILT_MESSAGE` is the "run `npm ci && npm run build`"
  text used both in the startup banner and as the page response when `web/dist` is missing.
- `api/live_snapshot.py` — `LiveSnapshot`, a lock-guarded, TTL-coalesced (`LIVE_TTL_SECONDS = 1.0`)
  wrapper around `claude_sessions.load_sessions()` + `claude_context.live_context()` per session, so
  N browsers/phones polling `/api/live` every ~2s cost about one recompute per second rather than N —
  those two modules' caches were written assuming a single Streamlit script thread, so every read of
  them from the API goes through this one lock. One session's `live_context()` raising leaves the
  others populated (`context: null` for that one). `is_live_now()` bypasses the TTL for delete
  decisions (see the `DELETE /api/sessions/{id}` route above); `cwd_for()` is used server-side only,
  never sent to a client.
- `api/overview_stats.py` — the pure aggregation lifted out of `views/overview.py`, with no pandas or
  Streamlit: `TIME_RANGES` (same table/semantics as `_TIME_RANGES`), `filter_by_range`,
  `project_totals` (top-7 + `"Other"`, `share`/`messages_pct`/`cost_pct`), `hourly_activity`
  (24-hour buckets trimmed to the contiguous active range, `sessions_pct`/`messages_pct`),
  `format_duration`, and `summary()` (the KPI figures, extremes annotated with `project`/`session_id`
  via `_with_session`). `overview()` ties it together into the `/api/overview` response, including
  `project_order` — the one ordering every chart on the page uses so a project's color never shifts
  between them.
- `api/transcript_query.py` — the pure port of `views/sessions_data.py`'s All-table filter/sort:
  `filter_transcripts` (literal case-insensitive substring over session ID/last message/first prompt,
  AND-combined with project/version/branch membership), `sort_transcripts` (stable, missing values
  last either direction), `filter_options` (distinct non-blank values per filterable field), and
  `query()` which combines all of that plus paging (`limit`/`offset`, default page size 50) into a
  `Page(items, total, options)`.

### `web/` — the React + TypeScript frontend

Vite + React + TypeScript + React Router + TanStack Query; plain hand-written CSS (no component
library). `npm run dev` proxies `/api` to `http://127.0.0.1:8501` (`vite.config.ts`) so the dev
server and the built app are both effectively same-origin. `web/src/main.tsx` wires up
`QueryClientProvider`/`BrowserRouter`; `App.tsx` is the route table (`/` → Sessions, `/overview`,
`/projects`, everything else redirects to `/`, since the server's SPA fallback can land any unknown
path here) rendered inside `AppShell`.

- **API layer** (`web/src/api/`): `client.ts`'s `apiFetch` is the one place that calls `fetch` —
  it adds `X-Requested-With: ledger` on non-GET requests (matching `security.py`'s CSRF check),
  and turns every failure into one of `ApiError` (the server answered with a non-2xx; carries
  FastAPI's `detail` message), `UnauthorizedError` (401 — this device isn't signed in), or
  `NetworkError` (fetch itself failed/threw). `queries.ts` has one TanStack Query hook per endpoint
  (`useMeta`, `useRefresh`, `useLive`, `useTranscripts` — an `useInfiniteQuery` for "Load more"
  paging, `useSession`, `useOverview`, `useProjects`, `useDeleteSession`, `useDeleteProject`);
  `useLive({auto})` sets `refetchInterval` to `2000` or `false` and disables background polling so a
  hidden tab stops hitting the server. `queryClient.ts` retries a dropped connection once
  (`NetworkError`) but never retries a real API error. `serverStatus.ts`'s `useServerProblem()` scans
  the query cache for failing *observed* queries (ones a mounted component is still watching) to
  decide what banner, if any, `AppShell` should show (`unauthorized` beats `error` beats
  `unreachable`), and clears itself once a retried query succeeds. `types.ts` mirrors the server's
  JSON shapes 1:1 (dates as ISO strings; the client formats/`--`s them).
- **Shell** (`web/src/components/AppShell.tsx`, `Nav.tsx`, `RefreshControl.tsx`, `ServerBanner.tsx`,
  `ThemeToggle.tsx`): `AppShell` picks a `useViewportClass()` (`narrow`/`medium`/`wide`, matchMedia
  at 640/1024px, `hooks/useViewportClass.ts`) and renders `Nav` as a top bar (medium/wide) or a fixed
  bottom tab bar (narrow, `viewport !== "narrow"` puts it in the header instead). `ServerBanner`
  shows a dismissible-by-retry notice above the page when a query is failing but keeps the page's
  last data visible underneath; `unauthorized` instead swaps the whole `<Outlet/>` for `SignInNeeded`
  (pointing back at the printed URL/QR).
- **Theme** (`theme/theme.ts`): `data-theme` on `<html>`, seeded from `localStorage` (guarded
  try/catch — private windows etc.) else `prefers-color-scheme`, applied *before* React even mounts.
  A module-level store (not per-component `useState`) notifies every subscriber — the toggle button
  and every chart that needs to recolor on theme change — via `useSyncExternalStore`, the same
  pattern `useViewportClass` uses; a live media-query listener keeps it in sync with the OS if
  nothing's been explicitly chosen yet. `theme/tokens.css` holds the light/dark CSS variables,
  including the 8-slot categorical palette (`--cat-0`..`--cat-7`) and `--muted-ink`, ported from
  `views/overview.py`'s `_CATEGORICAL_LIGHT`/`_CATEGORICAL_DARK`/`_MUTED_INK` — same fixed slot order,
  so a chart's `chartColors()`/`themeColors()` (see below) never has to duplicate a hex value.
- **Responsive list** (`components/list/`): `ResponsiveList` picks `ListTable` (medium/wide) or
  `ListCards` (narrow) by viewport — only one is ever mounted, both take the same `columns`/`rows`/
  `rowId`/`onSelect`, so switching layouts never changes what's shown or its order. A `ListColumn`
  carries a table `priority` (`"high"` shown at medium+, `"low"` only at wide) and an independent
  `cardPriority` (`"primary"`/`"secondary"`/`"hidden"`, defaulted from `priority` when omitted) for
  the narrow card layout, plus an optional `sortKey` that makes `ListTable`'s header (or `AllList`'s
  narrow-screen "Sort by" `<select>`, since cards have no headers) clickable/sortable.
- **Sessions** (`components/sessions/`, `pages/SessionsPage.tsx`): the open detail view lives in the
  URL (`?session=<id>&from=live|all`), not component state, so a reload/shared link reopens it and
  `SessionDialog` can stay mounted across selections rather than being conditionally rendered — that
  mounted-ness is what lets a Live poll update its content in place without losing scroll position
  (the dialog is a native `<dialog>`, opened with `showModal()`, so Esc/focus-trapping/inert
  background come for free; CSS turns it into a full-screen sheet under 640px). `LiveList` polls via
  `useLive`, with its own "Auto-refresh" switch and frozen "Last refreshed" caption when off.
  `AllList` debounces its search box (`useDebouncedValue`, 300ms), drives `Project`/`Version`/`Branch`
  `FilterMultiselect`s (`<details>`-based checkbox lists — no popover/portal machinery needed) off
  the API's option lists, and pages 50-at-a-time via `useTranscripts`'s "Load more". `SessionDialog`
  shows the recap block only when opened `from="all"` (ported from `sessions_context.py`'s
  `_render_recap`); its `Detail` section (current-context figure, `TokensChart`, "All responses"
  table, "what filled the context" by-tool/largest-increases tables) and `DeleteControls`
  (confirm/cancel → `useDeleteSession`, disabled with a note when live, a 409 mid-confirm surfaces
  the server's message) are ports of `_render_detail`/`_render_delete_controls`. `TokensChart` lazily
  `import()`s `vega-embed` (so the Sessions page, the first thing a phone opens, doesn't pay for its
  bundle cost until a detail view needs it) and rebuilds/re-embeds its spec whenever the turns or the
  theme change; its stacked-bar/cache-miss-triangle/compaction-rule spec mirrors
  `sessions_context.py`'s `_render_history_chart` field-for-field.
- **Overview** (`components/overview/`, `pages/OverviewPage.tsx`): `TimeRangeSelector` is a
  horizontally-scrollable segmented control over the same seven ranges as `_TIME_RANGES`.
  `chartTheme.ts`'s `chartColors()`/`projectColorScale()`/`projectColorMap()` centralize reading the
  CSS-variable palette and turning the API's `project_order` into a Vega-Lite domain/range (`"Other"`
  always the muted ink) shared by `ProjectDonutChart` and `ProjectBarChart`; `ProjectDonutChart` draws
  its own color key as a plain HTML list (`ProjectLegend`) instead of a Vega-Lite legend so long
  project names wrap instead of clipping. `ProjectBarChart` ("Messages & Cost by Project") and
  `HourlyBarChart` ("Activity by Hour of Day") both normalize each measure to % of its own peak (a
  deliberate non-dual-axis choice, matching `views/overview.py`) and keep "Messages" on the same
  categorical hue (`hues[0]`) in both charts. All three charts use the shared `useVegaEmbed` hook
  (lazy `vega-embed` import, re-embeds on spec change, `useVegaEmbed.ts` — the general form of the
  pattern `TokensChart` uses directly). `SummaryStats` renders the KPI tiles; the four extreme
  figures are buttons that toggle an inline disclosure naming their project/session (plus a `title`
  attribute for hover on pointer devices) since there's no hover-only affordance on a touchscreen.
- **`pages/ProjectsPage.tsx` is currently a stub** — just an `<h1>`. Building it out (list + delete
  flow, matching `streamlit_app/views/projects.py`'s behavior) is tasks.md §8, not yet done.
- **`lib/format.ts`** — display formatting for API values (`formatTime`, `formatDateTime`,
  `formatCost`, `formatContext`, `formatText`, `formatCount`; every one renders `"--"` for a missing
  value). **`lib/tokens.ts`** — `humanizeTokens`/`formatGrowth`, a deliberate port of
  `claude_context.py`'s `humanise_tokens`/`format_growth` so the two languages agree on what a
  context figure reads as (the API already sends a ready-made `label` string for the Live list from
  the Python formatter directly; these are for the raw numbers the API sends elsewhere — the All
  list's Context column, the detail view's "Current context" figure).

### `hooks/`

A standalone utility, unrelated to either dashboard UI: Windows toast notifications for Claude
Code's `Notification`/`Stop` hook events, with `Install-ClaudeHooks.ps1`/`Uninstall-ClaudeHooks.ps1`
to set them up on a machine. See `hooks/README.md` for how it works and full install/uninstall/test
steps.

### `openspec/`

The OpenSpec workflow directory: `openspec/specs/` holds the current, agreed specs for shipped
capabilities (`live-context-gauge`, `toast-context-line`); `openspec/changes/` holds proposals in
flight, each with `proposal.md`/`design.md`/`tasks.md` and (once merged) a spec delta —
`migrate-to-react-lan-access` (see "Project" above) is the active one; `openspec/changes/archive/`
holds completed ones. Treat these as the authoritative record of *why* a capability exists and what
it's required to do, ahead of inferring intent from the code alone.

### Other repo files

- `.streamlit/config.toml` holds Streamlit config (theme, server settings); `.streamlit/secrets.toml`
  (if created) and `.streamlit/theme_pref.json` are gitignored, as is `.streamlit/ledger.db*` (the
  SQLite snapshot both UIs currently read — see "Shared data layer" above). `.gitignore` also already
  has `.ledger/`, `web/node_modules/`, and `web/dist/` staged for when the DB-path/build-output
  migration tasks land.
- `requirements.txt`: `streamlit`, `pandas` (Streamlit side), `fastapi`, `uvicorn`, `qrcode` (API
  side) — unpinned. `requirements-dev.txt` adds `pytest`, `httpx` (for FastAPI's `TestClient`).
- `web/package.json`: React 19, `@tanstack/react-query`, `react-router-dom`, `vega-embed`
  (dependencies); Vite, TypeScript, Vitest, Testing Library, jsdom (devDependencies). `npm run build`
  is `tsc --noEmit && vite build` — a type error fails the build, not just lint.
