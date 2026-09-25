# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A dashboard for viewing your local Claude Code sessions and projects: Overview, Sessions (Live +
All), Projects. It's an API-only FastAPI backend (`api/`) plus one React + Vite frontend (`web/`),
built so a phone or other device on the same network can read it too, behind a shared access token.
The backend and frontend run as two separate processes/ports; the API never serves any HTML itself (see
"Setup & Run" below).

The repo has exactly four top-level folders, one per service, each self-contained: `api/` (the
backend — every Python module, its tests, `requirements*.txt`, `pyproject.toml`, and its own
gitignored `.venv`/`.ledger`), `web/` (the frontend), `gateway/` (the containerized Nginx reverse
proxy that's the only thing granting other devices access — its own Dockerfile, Nginx config
template, and compose file; see "From another device on your network" below), and `hooks/` (Claude
Code toast hooks, plus one optional relay hook coupled to the dashboard — see "`hooks/`" below). The root holds only cross-cutting docs/tooling (`README.md`, `CLAUDE.md`,
`.gitignore`, `.env.example`, `openspec/`, `.claude/`) plus a pair of scripts, `Start-Ledger.ps1`/
`Stop-Ledger.ps1` (and that pair's own gitignored state file, `.ledger-run.json`), kept at root
rather than inside any one service folder since they're the one piece of tooling that spans all
three equally (see "Setup & Run" below) — otherwise nothing at root runs on its own.

The agreed requirements for each shipped capability live in `openspec/specs/` (see "`openspec/`"
below) — check there for what a feature is required to do (e.g. `network-access` for the
bearer-token auth and separate-origin rules) ahead of inferring it from the code alone.

The API and frontend both read the same on-disk Claude Code data (`~/.claude.json` and
`~/.claude/projects/*/*.jsonl`) via a SQLite snapshot at `api/.ledger/ledger.db` (gitignored, rebuilt
from disk on every server start and periodically thereafter — see "Data layer" below).

## Setup & Run

Create/activate the venv and install Python dependencies, all inside `api/`:

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

A `.venv` already exists at `api/.venv` with dependencies installed — activate it
(`api\.venv\Scripts\Activate.ps1`, or invoke `api\.venv\Scripts\python.exe` /
`api\.venv\Scripts\pytest.exe` directly) rather than searching for or recreating one.

The frontend needs Node.js in addition to the Python setup above. It's built once (`npm run build`)
and then served by `vite preview`, which serves only the already-built `web/dist` — it doesn't
rebuild on save. `npm run dev` (hot-reloading, proxies `/api` to the backend) is available instead
while actively working on the frontend, but isn't what's used for normal local use.

**Two processes, two ports, every time** — the API only ever serves `/api/*`; the frontend is
always its own separate process:

```powershell
# Terminal 1, in api/: the API (defaults to http://localhost:8501)
cd api
python server.py

# Terminal 2, in web/: build once, then serve the built frontend (defaults to http://localhost:4173)
cd web
npm ci
npm run build
npm run preview
```

Open the frontend's URL (http://localhost:4173 by default), not the API's — the API has no page to
show you.

**Or start everything at once** with the root `Start-Ledger.ps1`, which runs the two processes
above (each in its own window, so their logs/Ctrl+C stay independent) plus the gateway described
below, in one call — paired with `Stop-Ledger.ps1` to stop exactly what it started (backend/frontend
window PIDs recorded to the root `.ledger-run.json`, gitignored, and the gateway container):

```powershell
.\Start-Ledger.ps1              # build mode (default) — matches normal local use
.\Start-Ledger.ps1 -Mode dev    # backend + frontend as hot-reloading dev servers instead
.\Start-Ledger.ps1 -NoGateway   # skip the gateway container (this machine only)
.\Stop-Ledger.ps1               # stop the backend/frontend windows and the gateway
```

`-Mode` changes how both the backend and frontend windows start — the gateway always starts the
same way either way. `build` runs `npm run build` + `npm run preview` and starts the backend
without `--reload`; `dev` runs `npm run dev` and starts the backend with `python server.py
--reload` (uvicorn restarts the process on any saved change under `api/`). Port overrides
(`-BackendPort`/`-FrontendPort`/`-GatewayPort`) follow the same `.env` precedence as
`gateway\Start-Gateway.ps1` (see below).

`server.py --reload` (also usable directly, outside `Start-Ledger.ps1`) only works because uvicorn
is given `"server:app"` as an import string rather than the already-constructed `app` object — that
lets it re-import the module fresh in a new subprocess on every change, which is also why the
backend's startup banner and access-token print in the terminal are only accurate for the very
first start of a `--reload` session (each subsequent restart re-provisions the same stored token
silently in `lifespan()`, since the freshly re-imported module never runs `main()` again).

**From another device on your network** (phone, tablet, another computer): the backend and frontend
above never bind beyond loopback, no matter what — the only thing that ever grants LAN access is a
containerized Nginx gateway, started as its own third piece alongside the two processes above.
Requires Docker Desktop (Windows/Mac; this relies on `host.docker.internal` reaching a
loopback-only bind, a Docker Desktop behavior — see
`openspec/changes/add-nginx-lan-gateway/design.md`). With the backend and frontend already
running:

```powershell
cd gateway
.\Start-Gateway.ps1
```

This builds/starts the gateway container (Nginx, published on `GATEWAY_PORT`, default `8080`) and
then prints the sign-in link/QR for every address this machine is reachable at — e.g.
`https://<address>:8080/?token=<token>` — via `api/gateway_signin.py`. The gateway serves **HTTPS
only**, with a self-signed certificate (there's no plain-HTTP listener to fall back to), so each
new device's browser shows a one-time certificate warning on first visit — expected, not a
misconfiguration; accept it once. An old `http://` sign-in link no longer works: re-run
`Start-Gateway.ps1` and use the freshly printed `https://` one. Opening that link on another
device signs it in (the token is stored in that browser's `localStorage` and stripped from the
address bar) and every subsequent request from it carries `Authorization: Bearer <token>`. A local
request (from this machine, via `localhost`/`127.0.0.1`) needs no token at all; every other request
needs it, checked by `api/security.py`'s `SecurityMiddleware` (see "Architecture" below) exactly as
before — the gateway adds no auth of its own, it only relays. A token is not enough for everything,
though: deleting a session/project and switching Remote mode need a *local* request outright, and
answering a live session's prompts from another device needs Remote mode on (see "Architecture"
below). Only do this on a network you trust — the certificate is self-signed, so the encryption
protects against snooping but the browser can't vouch for who it's talking to. Windows will prompt to allow Docker/the gateway through the firewall the first time — allow it on
Private networks. Stop it with `.\Stop-Gateway.ps1`; it doesn't touch the backend/frontend
processes.

**`GATEWAY_PORT` must not be one of Chromium's restricted ports** (e.g. `10080`, which was this
project's own original default and broke exactly this way) — Chrome, and every Chromium-based
mobile browser, silently refuses to even attempt a connection to those ports (`ERR_UNSAFE_PORT`),
with nothing to see server-side: `curl`/`Test-NetConnection` and the like still succeed, only actual
browsers fail, which makes this easy to misdiagnose as a firewall or Docker networking problem. Pick
an ordinary high port instead (`8080`, or anything else not on Chromium's list).

To rotate the access token (e.g. after sharing it), delete `api/.ledger/token` and restart the
backend; a fresh one is generated on next start (token provisioning is unconditional now, not tied
to any LAN flag). Setting `LEDGER_TOKEN` in the environment overrides the stored file entirely.

The backend's `--host`/`--port`/`--frontend-port` (or `LEDGER_HOST`/`LEDGER_PORT`/
`LEDGER_FRONTEND_PORT` env vars) still override its own bind address/port and the port it prints a
frontend link for — `--frontend-port` is cosmetic only now (CORS is gone entirely, since the
frontend never calls the backend cross-origin any more). Passing `--lan` is a removed no-op: it
exits with an error pointing at the gateway instead.

**One place to see every port at a glance**: copy root `.env.example` to `.env` (gitignored) and
edit `BACKEND_PORT`/`FRONTEND_PORT`/`GATEWAY_PORT` there. `Start-Gateway.ps1`/
`gateway/docker-compose.yml` read it directly — it's the source of truth for what port Nginx
proxies `/api/*` and `/` to inside the container. The backend and frontend themselves are still
separate local processes that don't read this file: if you change `BACKEND_PORT`/`FRONTEND_PORT`
away from the defaults (8501/4173), also pass `python server.py --port <BACKEND_PORT>` and
`npm run preview -- --port <FRONTEND_PORT>` so they actually run on the ports the gateway expects,
or the gateway will fail to reach them. A custom `BACKEND_PORT` also needs to be set in the
frontend process's own environment (e.g. `BACKEND_PORT=<port> npm run preview -- --port
<FRONTEND_PORT>`) — `web/vite.config.ts`'s own `/api` proxy (used for direct, non-gateway access)
reads it from `process.env.BACKEND_PORT` (default `8501`), separately from the port the gateway's
Nginx is told to target.

Dark/light theme is chosen per device, not shared server-side: each browser picks up
`prefers-color-scheme` until it toggles the switch itself, then remembers that choice in its own
`localStorage` (see `web/src/theme/theme.ts`).

## Testing

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
                   # list/ResponsiveList, projects/ProjectsList (delete hidden off-machine),
                   # sessions/DecisionPrompt, sessions/RemoteModeControl, hooks/useDebouncedValue,
                   # hooks/useViewportClass, lib/format, lib/tokens
npm run build      # tsc --noEmit, then vite build -> web/dist
```

There is no browser-automation/E2E harness for the React app; responsive layout across breakpoints
is verified manually (resizing a real browser, and a real phone through the gateway — see "From
another device on your network" above).

## Architecture

### Data layer (`api/claude_*.py`)

These modules live in `api/` alongside the server (their only consumer), but are plain Python with
no FastAPI/Starlette dependency of their own — keeping them framework-free keeps the pure data layer
testable and readable independent of the web framework wrapping it.

- `claude_db.py` is the single SQLite-backed store that `claude_projects.py` and
  `claude_transcripts.py` both read from, rather than each independently scanning and mtime-caching
  its own file(s) on disk as they used to. All of that disk-reading — `~/.claude.json` and
  `~/.claude/projects/*/*.jsonl` parsing, the `_MODEL_PRICING` table, `sanitize_project_path()`, etc.
  — lives here. `refresh()` rescans both sources, resolves each transcript's `project` from the
  just-scanned project list (matching the transcript's on-disk parent folder against
  `sanitize_project_path()`), replaces the `projects`/`transcripts` tables' contents in one pass, and
  stamps a `meta.refreshed_at` timestamp; `refreshed_at()` reads that timestamp back. This is the
  *only* place disk gets rescanned — triggered explicitly via `POST /api/refresh`, plus once
  automatically via `startup()` on process start, plus a periodic 10-minute `asyncio` loop task (see
  `api/server.py`). `startup()` treats the database as a pure derived cache: it deletes any leftover
  db file from a previous run, calls `refresh()` to rebuild it from disk, and registers an `atexit`
  handler to delete it again on exit (best-effort). `db_path()` returns `api/.ledger/ledger.db` (gitignored;
  that `.ledger/` is also where the LAN access token lives — see `api/security.py` below).
  `_connect()` sets `PRAGMA journal_mode=WAL` and a busy timeout, for the FastAPI server's
  concurrent-request model (multiple browsers/phones reading while a background `refresh()` writes);
  `startup()`/its `atexit` hook also clean up the `-wal`/`-shm` files. `load_projects()` /
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
  growth, a block-glyph sparkline scaled 0→window-max). The API's `live_snapshot.py` calls this
  function directly so the Live list's `label` text comes straight from it. For the detail dialog/
  view, `load_detail()` fully parses the transcript on demand into per-turn records plus
  `compact_boundary` compactions; growth attribution credits each turn's context delta to the first
  tool called in the previous turn (or "prompt / text"), since the latest compaction, with
  `first-turn context + attributed growth == current context` holding exactly. Main thread only —
  subagent transcripts are ignored.

### `api/` — the FastAPI backend

`api/server.py` is both the ASGI app and the CLI (`python server.py [--host] [--port]
[--frontend-port] [--reload]`, env `LEDGER_HOST`/`LEDGER_PORT`/`LEDGER_FRONTEND_PORT`; default host
`127.0.0.1` port `8501`). It always binds loopback only now — `--frontend-port` only controls the
printed frontend link, and `--lan` is still recognized by the parser but exits with an error
pointing at the gateway (`gateway/`) instead of binding `0.0.0.0`; the gateway container is the only
thing that ever grants LAN access (see CLAUDE.md's "Setup & Run" above). `--reload` (dev only, no
env var) restarts the process on any saved change under `api/`; it works by handing uvicorn the
import string `"server:app"` instead of the already-built `app` object, since only the string form
lets uvicorn re-import the module fresh per restart — which is also why `main()`'s own token
provisioning (see `lifespan` below) is duplicated, guarded, in `lifespan` itself: the reload
subprocess re-imports the module without ever calling `main()`. Every module it imports lives
alongside it in `api/`, so running it directly (which puts its own directory on `sys.path`) is all
the import setup it needs. Its `lifespan` calls `claude_db.startup()` in a worker thread on start and runs
a 10-minute `refresh_loop()` for as long as the process is up, both funneled through a process-wide
`_refresh_lock` shared with `POST /api/refresh` so a scan (which can take seconds on a big history)
is never triggered twice concurrently. It serves `/api/*` only — no HTML, no static assets; the
frontend is a wholly separate process (see `web/` below). Routes:

| Endpoint | Notes |
|---|---|
| `GET /api/meta` | `{refreshed_at, is_local, remote_mode: {enabled, expires_at}}` — `is_local` is `security.is_local(request)` for *this* request, so the frontend can hide controls a remote device can't use |
| `POST /api/remote-mode` | Body `{enabled}`; **local requests only** (403 otherwise, token or not). Returns the new `remote_mode` |
| `POST /api/refresh` | Forces a `locked_refresh()`, returns the new `refreshed_at` |
| `GET /api/live` | `{sessions: [...]}` from the shared `LiveSnapshot` (see `live_snapshot.py`); each session gains `pending_decision: {id, tool_name, tool_input} \| null` (its oldest pending prompt), always `null` for a non-local request while Remote mode is off. Sweeps stale prompts first |
| `GET /api/sessions/{id}/pending-decision` | `{pending_decision}`, same visibility rule as `/api/live`; polled by the Live control view |
| `POST /api/sessions/{id}/decisions` | **Relay hook only** (local requests only, 403 otherwise). Body `{tool_name, tool_input}`; registers the prompt and *holds the request open* until it's answered, cleared or times out, then returns `{decision: "allow" \| "deny" \| "answer" \| null, ...}` — `null` means "no answer", and the hook then prints nothing |
| `POST /api/sessions/{id}/decisions/{prompt_id}/answer` | The dashboard's answer: `{decision: "allow"}`, `{decision: "deny", reason?}` or `{decision: "answer", answers: {"<question>": string \| string[]}}`. 403 for a non-local request unless Remote mode is on; 409 if the prompt is gone (answered/cleared elsewhere); 422 if the shape doesn't fit the prompt kind (answers must cover exactly the questions asked, lists only for multi-select) |
| `POST /api/sessions/{id}/open-repo` | Opens the session's `cwd` (from the live registry — never a request parameter) in VS Code on the host; 404 unless the session is live. Token-gated like any other non-GET, no Remote-mode/locality requirement |
| `GET /api/transcripts` | `q`, `project[]`, `version[]`, `branch[]`, `sort`, `dir`, `limit`, `offset` → paged items + `total` + filter `options`, via `transcript_query.py`; each item's `live` flag comes from the same `LiveSnapshot`'s live-ID set |
| `GET /api/sessions/{id}` | Recap + `SessionDetail` JSON, or `readable: false`. `id` is validated against `^[A-Za-z0-9-]{1,64}$` at the route; `cwd` is resolved server-side from the live registry or the transcripts snapshot, **never** from a request parameter |
| `DELETE /api/sessions/{id}` | **Local requests only** (403 otherwise — a valid token doesn't authorize a delete); 409 if `live.is_live_now(id)` (a *fresh* registry read, not the ≤1s snapshot — a session that just started can't be deleted on stale data), 404 if unknown, else `claude_transcripts.delete_transcript` under the refresh lock |
| `GET /api/projects` | `{projects: [...]}` |
| `DELETE /api/projects?path=` | **Local requests only**, like the session delete; 404 unless `path` exactly matches a known project; then `delete_project` + `delete_project_transcripts` |
| `GET /api/overview?range=` | 422 for an unknown range label; otherwise `overview_stats.overview()`'s payload |

There's no static-file serving or SPA fallback here; that's `vite preview`'s job in `web/`.
`GZipMiddleware` and `SecurityMiddleware` (added first so it's outermost — nothing else runs for a
refused request) wrap every route. There is no `CORSMiddleware` at all: the frontend only ever
calls relative `/api/...` paths (`vite dev`'s proxy, `vite preview`'s proxy, or the gateway's proxy),
so no browser page is ever served from a different origin than the one it calls, and the backend
never receives a legitimate cross-origin request to allow (`test_server.py` asserts no
`CORSMiddleware` is registered).

- `api/security.py` — one ASGI middleware gating every request (its requirements are the `network-access` spec).
  A request is **local** only when `request.client.host` is loopback (`127.0.0.1`/`::1`/
  `::ffff:127.0.0.1`) *and* carries none of `Forwarded`/`X-Forwarded-For`/`X-Real-IP` (so a tunnel or
  reverse proxy on the same machine is treated as remote, not silently trusted); local requests must
  still present `Host: localhost`/`127.0.0.1`/`[::1]` (any port) or get a 403 — this stops a public DNS
  name that resolves to 127.0.0.1 from reaching the app unauthenticated. Every non-local request needs
  the access token as `Authorization: Bearer <token>` (`hmac.compare_digest` comparison) or gets a 401
  with a message pointing back at the printed sign-in link — there is no `?token=` query handling or
  cookie on the API side at all; turning a printed link's `?token=` into that header is entirely the
  frontend's job (see `web/src/api/token.ts` below). Every non-GET request additionally needs an
  `X-Requested-With: ledger` header, which a page on another origin can't add without a CORS
  preflight — with no `CORSMiddleware` at all now, that preflight always fails, so that header is
  what stops a blind cross-site `POST`/`DELETE` even from a page that could otherwise read the API.
  `provision_token()` runs unconditionally on every backend start now (no longer gated by a LAN
  flag) — it's `LEDGER_TOKEN` if set, else the token stored at `api/.ledger/token` (created with
  `secrets.token_urlsafe(32)` on first start, mode `0o600`) — delete that file and restart to rotate it.
  The middleware's locality test is also exported as `is_local(request)`, which is what makes some
  things stricter than "has the token": both `DELETE` routes, `POST /api/remote-mode` and
  `POST /api/sessions/{id}/decisions` call it and refuse a non-local request with 403 regardless of
  any token (so a remote device can read, and — with Remote mode on — answer prompts, but never
  delete or flip Remote mode), and `GET /api/meta` reports it back as `is_local` so the frontend can
  hide those controls up front. The route-level check is the actual security boundary; hiding the
  buttons is only UX.
- `api/banner.py` — what the server prints at startup: always a reminder that the frontend is a
  separate process and how to start it (`cd web && npm run preview`), plus its local URL — the
  backend has no LAN-facing state to report any more, so that's the whole banner (`build_banner()`).
  Its `discover_ipv4()` (a UDP-connect trick to find the outbound interface, plus hostname
  resolution, filtered by `usable_ipv4` to drop loopback/link-local/unspecified addresses) and
  `render_qr()` (ASCII QR via `qrcode`; `None` if the package or the terminal's encoding can't render
  it) are still here and still exercised by `test_banner.py`, but are no longer called from the
  backend's own startup path — `api/gateway_signin.py` reuses them instead (see `gateway/` below) to
  build the gateway's own sign-in banner/QR from the gateway side, once the gateway container starts.
- `api/live_snapshot.py` — `LiveSnapshot`, a lock-guarded, TTL-coalesced (`LIVE_TTL_SECONDS = 1.0`)
  wrapper around `claude_sessions.load_sessions()` + `claude_context.live_context()` per session, so
  N browsers/phones polling `/api/live` every ~2s cost about one recompute per second rather than N —
  those two modules' own caches assume a single caller, so every read of them from the API goes
  through this one lock. One session's `live_context()` raising leaves the others populated
  (`context: null` for that one). `is_live_now()` bypasses the TTL for delete decisions (see the
  `DELETE /api/sessions/{id}` route above); `cwd_for()` is used server-side only, never sent to a
  client. `latest_activity()` (through the same lock) feeds the pending-prompt sweep below.
- `api/pending_decisions.py` — `PendingDecisions`, the in-memory, lock-guarded store (same spirit as
  `LiveSnapshot`; nothing touches disk) behind answering a live session's blocking prompts from the
  dashboard, plus the **Remote mode** switch. The prompts come from the optional relay hook (see
  `hooks/` below): a `PermissionRequest` hook fires only when Claude Code is about to show a dialog
  (a tool-permission prompt or an `AskUserQuestion`), runs *alongside* the terminal dialog rather than
  in front of it, and POSTs the prompt to `/api/sessions/{id}/decisions`, which `register()`s it (an
  API-generated id, since Claude Code supplies none) and awaits it in `request_decision()`. Whichever
  surface answers first wins: a dashboard answer resolves the waiting request (`answer()`), which the
  hook hands back to Claude Code as the decision; a terminal answer is never heard directly, so
  `sweep()` clears the prompt when the session's transcript shows a new **`user`** line (the tool
  result) stamped after it was registered — only `user` lines count, since `assistant`/bookkeeping
  lines can appear while a dialog is still open — and releases the hook with "no answer" so it exits.
  A 30-minute maximum age is the backstop. `sweep()` isn't on a timer: `/api/live`, the
  pending-decision route and the answer route each run it first (`server._sweep_prompts`), so an
  already-answered prompt gives a 409 rather than "succeeding". **Remote mode** is only state here
  (`set_remote_mode`/`remote_mode`/`remote_mode_enabled`): in-memory, off after 8 hours and after any
  backend restart, and only a local request can turn it on or off. It is purely an access gate on
  *other devices* — the hook always registers prompts and never hides the terminal dialog — so while
  it's off a non-local request sees no pending prompt and can't answer one, while the PC's own
  browser always can (`server._can_see_prompts`).
- `POST /api/sessions/{id}/open-repo` shells out to `hooks/scripts/Open-ClaudeRepoWindow.ps1`
  (`server.OPEN_REPO_SCRIPT`, `subprocess.run`, the script unmodified) with a
  `claudecode://open?path=<url-encoded cwd>` URI — the repo's own copy, not the one installed under
  `%USERPROFILE%\.claude\hooks\`, so `api/` now depends on that file in `hooks/` even though `hooks/`
  is otherwise standalone. It needs no install step, only that the API run from this checkout.
- `api/overview_stats.py` — the pure aggregation behind `/api/overview`, no pandas: `TIME_RANGES`
  (All time/Today/Yesterday/Past week/Past month/Past quarter/Past year, bucketed by *local calendar
  date*, not a rolling window), `filter_by_range`, `project_totals` (top-7 + `"Other"`,
  `share`/`messages_pct`/`cost_pct`), `hourly_activity` (24-hour buckets trimmed to the contiguous
  active range, `sessions_pct`/`messages_pct`), `format_duration`, and `summary()` (the KPI figures,
  extremes annotated with `project`/`session_id` via `_with_session`). `overview()` ties it together
  into the `/api/overview` response, including `project_order` — the one ordering every chart on the
  page uses so a project's color never shifts between them.
- `api/transcript_query.py` — the filter/sort logic behind `/api/transcripts`: `filter_transcripts`
  (literal case-insensitive substring over session ID/last message/first prompt, AND-combined with
  project/version/branch membership), `sort_transcripts` (stable, missing values last either
  direction), `filter_options` (distinct non-blank values per filterable field), and `query()` which
  combines all of that plus paging (`limit`/`offset`, default page size 50) into a
  `Page(items, total, options)`.

### `web/` — the React + TypeScript frontend

Vite + React + TypeScript + React Router + TanStack Query; plain hand-written CSS (no component
library, no Sass): global stylesheets in `styles/` (`app.css`, `overview.css`, `sessions.css`) plus
`theme/tokens.css`, and newer components as colocated CSS modules (`Switch.tsx` +
`Switch.module.css`: one flat camelCase class per element, sizes/variants as component-scoped custom
properties, colours only from the `tokens.css` variables, `className` on the root element and every
other prop on the underlying control). Migrate a component to a module when touching it; don't
rewrite `styles/` wholesale. Inline SVG icons in `components/icons.tsx`. Both `npm run dev` and `npm run preview` proxy `/api` to
`http://127.0.0.1:8501` (`vite.config.ts`'s `server.proxy`/`preview.proxy`, kept in sync), so the
page is always same-origin with the API whether run directly or through the gateway — the frontend
never needs a different-origin API client. `web/src/main.tsx` wires up
`QueryClientProvider`/`BrowserRouter`; `App.tsx` is the route table (`/` → Sessions, `/overview`,
`/projects`, everything else redirects to `/`, since `vite preview`'s SPA fallback serves `index.html` for
any unknown path) rendered inside `AppShell`.

- **API layer** (`web/src/api/`): `token.ts` is the frontend's whole sign-in story —
  `consumeTokenFromUrl()` runs in `main.tsx` before React renders, stores a printed link's
  `?token=` in `localStorage` (try/catch-guarded) and strips it from the address bar via
  `history.replaceState`; `getStoredToken()` reads it back. `client.ts`'s `apiFetch` is the one
  place that calls `fetch` — it sends that token as `Authorization: Bearer <token>` when one is
  stored, adds `X-Requested-With: ledger` on non-GET requests (matching `security.py`'s CSRF check),
  and turns every failure into one of `ApiError` (the server answered with a non-2xx; carries
  FastAPI's `detail` message), `UnauthorizedError` (401 — this device isn't signed in), or
  `NetworkError` (fetch itself failed/threw). `queries.ts` has one TanStack Query hook per endpoint
  (`useMeta`, `useRefresh`, `useLive`, `useTranscripts` — an `useInfiniteQuery` for "Load more"
  paging, `useSession`, `useOverview`, `useProjects`, `useDeleteSession`, `useDeleteProject`,
  `usePendingDecision`, `useAnswerDecision`, `useSetRemoteMode`, `useOpenRepo`);
  `useLive({auto})` sets `refetchInterval` to `2000` or `false` and disables background polling so a
  hidden tab stops hitting the server. `queryClient.ts` retries a dropped connection once
  (`NetworkError`) but never retries a real API error. `serverStatus.ts`'s `useServerProblem()` scans
  the query cache for failing *observed* queries (ones a mounted component is still watching) to
  decide what banner, if any, `AppShell` should show (`unauthorized` beats `error` beats
  `unreachable`), and clears itself once a retried query succeeds. `types.ts` mirrors the server's
  JSON shapes 1:1 (dates as ISO strings; the client formats/`--`s them).
- **Shell** (`web/src/components/AppShell.tsx`, `Nav.tsx`, `RefreshControl.tsx`, `ServerBanner.tsx`,
  `ThemeToggle.tsx`): `AppShell` picks a `useViewportClass()` (`narrow`/`medium`/`wide`, matchMedia
  at 640/1024px, `hooks/useViewportClass.ts`; the boundaries live only in `src/lib/breakpoints.ts`, and the
  stylesheets write `@media (--narrow)`/`(--medium-up)`/`(--wide-up)`, which `web/build/mediaAliases.ts`, a
  PostCSS plugin wired in `vite.config.ts`, swaps for the real queries at build time) and renders `Nav` as a top bar (medium/wide) or a fixed
  bottom tab bar (narrow, `viewport !== "narrow"` puts it in the header instead). `ServerBanner`
  shows a dismissible-by-retry notice above the page when a query is failing but keeps the page's
  last data visible underneath; `unauthorized` instead swaps the whole `<Outlet/>` for `SignInNeeded`
  (pointing back at the printed URL/QR).
- **Theme** (`theme/theme.ts`): `data-theme` on `<html>`, seeded from `localStorage` (guarded
  try/catch — private windows etc.) else `prefers-color-scheme`, applied *before* React even mounts.
  A module-level store (not per-component `useState`) notifies every subscriber — the toggle button
  and every chart that needs to recolor on theme change — via `useSyncExternalStore`, the same
  pattern `useViewportClass` uses; a live media-query listener keeps it in sync with the OS if
  nothing's been explicitly chosen yet. `theme/tokens.css` holds the light/dark CSS variables:
  the palette (backgrounds, text, brand, borders, feedback, syntax, shadows, inputs) and font families
  are a manual copy of `@joisse1101/ui-library`'s theme variables under that library's own names
  (`--bg-main`, `--text-main`, `--brand-accent`, `--brand-text`, `--syntax-keyword`, …; provenance and
  version are in the file's header comment), so components copied from the library work unchanged.
  The package is **not** a dependency — refresh by re-copying the variable blocks from its
  `dist/ui-library.css`. App-only tokens with no library equivalent stay alongside: the 8-slot
  categorical palette (`--cat-0`..`--cat-7`, fixed slot order so a chart's `chartColors()`/
  `themeColors()` (see below) never has to duplicate a hex value), `--muted-ink`, and
  `--warn-bg`/`--warn-text`. Fonts (Figtree/Urbanist/JetBrains Mono) load from Google Fonts via
  `index.html`, falling back to system fonts offline; the heading/link/code rules in `app.css`
  mirror the library's `_core_theme.scss`.
- **Responsive list** (`components/list/`): `ResponsiveList` picks `ListTable` (medium/wide) or
  `ListCards` (narrow) by viewport — only one is ever mounted, both take the same `columns`/`rows`/
  `rowId`/`onSelect`, so switching layouts never changes what's shown or its order. A `ListColumn`
  carries a table `priority` (`"high"` shown at medium+, `"low"` only at wide) and an independent
  `cardPriority` (`"primary"`/`"secondary"`/`"hidden"`, defaulted from `priority` when omitted) for
  the narrow card layout, plus an optional `sortKey` that makes `ListTable`'s header (or `AllList`'s
  narrow-screen "Sort by" `<select>`, since cards have no headers) clickable/sortable.
- **Sessions** (`components/sessions/`, `pages/LiveSessionsPage.tsx` at `/`, `pages/SessionsPage.tsx` at
  `/sessions`): Live and All are separate pages. Each keeps its selection in the URL (`?session=<id>`),
  so a reload/shared link reopens it. **Live** (`LiveSessionsPage`): `LiveList` polls via `useLive`, with
  its own "Auto-refresh" switch and frozen "Last refreshed" caption when off; selecting a row renders
  `LiveSessionPanel` *under the list* (not a dialog) with `LiveControl` — a control-only view: the
  session's oldest pending prompt rendered by `DecisionPrompt` (Approve/Deny with an optional reason
  for a permission prompt; the real options, multi-select and free text for an `AskUserQuestion`, via
  `lib/prompt.ts`) and an "Open repo window" button (`useOpenRepo`). The panel reads the Live list from
  the query cache with `auto: false`, so only `LiveList`'s switch drives polling.
  `usePendingDecision` polls while it's mounted; a prompt that vanishes without this view having
  answered it says the session already moved on (as does a 409) instead of going blank, and it shows
  nothing on a non-local device while Remote mode is off. `LiveList` badges a row (`pending-badge`)
  from `/api/live`'s `pending_decision`, and carries `RemoteModeControl`: a switch on the machine
  running the app (`is_local`), read-only "Remote mode: on, 7h left" text elsewhere. **All**
  (`SessionsPage`): `AllList` debounces its search box (`useDebouncedValue`, 300ms), drives
  `Project`/`Version`/`Branch` `FilterMultiselect`s (`<details>`-based checkbox lists — no
  popover/portal machinery needed) off the API's option lists, and pages 50-at-a-time via
  `useTranscripts`'s "Load more". A row opens `SessionDialog`, a native `<dialog>` (`showModal()`, so
  Esc/focus-trapping/inert background come for free; CSS turns it into a full-screen sheet under
  640px) kept mounted across selections so a poll updates it in place without losing scroll position.
  It shows the recap block, its `Detail` section (current-context figure, `TokensChart`, "All
  responses" table, "what filled the context" by-tool/largest-increases tables) and `DeleteControls`
  (confirm/cancel → `useDeleteSession`, disabled with a note when live, a 409 mid-confirm surfaces the
  server's message; hidden entirely when `useMeta().is_local` is false). `TokensChart` lazily
  `import()`s `vega-embed` (so the Sessions page, the first thing a phone opens, doesn't pay for its
  bundle cost until a detail view needs it) and rebuilds/re-embeds its spec whenever the turns or the
  theme change; its spec draws the stacked Cache read/Cache written/New bars with ▼ cache-miss markers
  and dashed compaction rules.
- **Overview** (`components/overview/`, `pages/OverviewPage.tsx`): `TimeRangeSelector` is a
  horizontally-scrollable segmented control over the same seven ranges as `overview_stats.TIME_RANGES`.
  `chartTheme.ts`'s `chartColors()`/`projectColorScale()`/`projectColorMap()` centralize reading the
  CSS-variable palette and turning the API's `project_order` into a Vega-Lite domain/range (`"Other"`
  always the muted ink) shared by `ProjectDonutChart` and `ProjectBarChart`; `ProjectDonutChart` draws
  its own color key as a plain HTML list (`ProjectLegend`) instead of a Vega-Lite legend so long
  project names wrap instead of clipping. `ProjectBarChart` ("Messages & Cost by Project") and
  `HourlyBarChart` ("Activity by Hour of Day") both normalize each measure to % of its own peak (a
  deliberate non-dual-axis choice so two differently-scaled measures can share one axis) and keep
  "Messages" on the same categorical hue (`hues[0]`) in both charts. All three charts use the shared `useVegaEmbed` hook
  (lazy `vega-embed` import, re-embeds on spec change, `useVegaEmbed.ts` — the general form of the
  pattern `TokensChart` uses directly). `SummaryStats` renders the KPI tiles; the four extreme
  figures are buttons that toggle an inline disclosure naming their project/session (plus a `title`
  attribute for hover on pointer devices) since there's no hover-only affordance on a touchscreen.
- **Projects** (`components/projects/ProjectsList.tsx`, `pages/ProjectsPage.tsx`) renders every
  field from `useProjects()` (name, path, trust, last session, version, last cost, last start, lines
  +/-, MCP servers) through the same `ResponsiveList` the Sessions lists use. There's no per-project
  detail view here, so — unlike
  Sessions, where a row click opens a dialog — a row click doubles as "delete this one" (a
  dedicated per-row delete button isn't possible without nesting a `<button>` inside `ListCards`'
  card-as-button); selecting a row shows an inline `detail-notice` confirmation naming the exact
  path before Confirm/Cancel — but only when `useMeta().is_local`; on another device a row click
  does nothing, since the API refuses remote deletes. Confirming calls `useDeleteProject`, whose `onSuccess` already
  invalidates the `projects`, `transcripts`, and `overview` queries.
- **`lib/format.ts`** — display formatting for API values (`formatTime`, `formatDateTime`,
  `formatCost`, `formatContext`, `formatText`, `formatCount`; every one renders `"--"` for a missing
  value). **`lib/tokens.ts`** — `humanizeTokens`/`formatGrowth`, a deliberate port of
  `claude_context.py`'s `humanise_tokens`/`format_growth` so the two languages agree on what a
  context figure reads as (the API already sends a ready-made `label` string for the Live list from
  the Python formatter directly; these are for the raw numbers the API sends elsewhere — the All
  list's Context column, the detail view's "Current context" figure).

### `gateway/` — the containerized Nginx reverse proxy

The only thing that ever grants LAN access (see CLAUDE.md's "Setup & Run" above); the backend and
frontend stay loopback-only always. It **terminates TLS and serves HTTPS only**: the `Dockerfile`
installs `openssl` at image build time to generate a self-signed EC certificate/key
(`/etc/nginx/certs/gateway.{crt,key}`, 10-year validity, `CN=the-ledger-gateway`, SANs for
`localhost`/`127.0.0.1`), then removes it again; Docker's layer cache keeps the same certificate
across rebuilds, so a device that accepted it once isn't warned again until that layer is rebuilt.
The template has a single `listen 443 ssl;` server (TLS 1.2/1.3) — no plain-HTTP listener at all, so
nothing can be downgraded — and `docker-compose.yml` maps `${GATEWAY_PORT:-8080}` to container port
443. The hop behind it (gateway → `host.docker.internal` → backend/frontend) stays plain HTTP: it's
loopback-only on the host, so the gateway-to-device hop is the only one that's on the network at
all. A LAN address has no stable hostname to get a real CA certificate for, hence self-signed and
the one-time browser warning per device. `Dockerfile` builds `nginx:alpine` with `nginx.conf.template`
copied to `/etc/nginx/templates/default.conf.template` — the base image's entrypoint runs `envsubst`
on it at container start, substituting `${BACKEND_PORT}`/`${FRONTEND_PORT}` (left in the template as
literal `$host`/`$remote_addr`/`$proxy_add_x_forwarded_for` for Nginx itself, since `envsubst` only
touches names that are actually set environment variables) into
`/etc/nginx/conf.d/default.conf`. `location /api/` proxies to
`http://host.docker.internal:${BACKEND_PORT}`; `location /` proxies to
`http://host.docker.internal:${FRONTEND_PORT}` — `host.docker.internal` is Docker Desktop's
mechanism for a container to reach a host process bound to loopback only (Windows/Mac only; this is
why the gateway needs Docker Desktop specifically). Both locations forward
`X-Real-IP`/`X-Forwarded-For`/`Host`, so `api/security.py`'s existing "relayed by a proxy = treat as
remote" rule gates gateway traffic exactly like it always gated the old `--lan` mode — the gateway
adds no auth of its own. `docker-compose.yml` publishes the container on `${GATEWAY_PORT:-8080}`
and passes `BACKEND_PORT`/`FRONTEND_PORT` through as container environment variables (defaults
8501/4173). `Start-Gateway.ps1` loads the root `.env` (see "Setup & Run" above), runs
`docker compose up -d --build`, then calls `api/gateway_signin.py` to print the sign-in banner/QR;
`Stop-Gateway.ps1` runs `docker compose down` and touches nothing else. `api/gateway_signin.py`
prints `https://` links and encodes the QR with the same HTTPS address, with a note that the
self-signed certificate will draw a one-time browser warning; it
reads the already-provisioned token from `api/.ledger/token` and reuses `banner.discover_ipv4()`/
`banner.render_qr()` (not its own copy) so address-discovery logic still lives in exactly one place.

### `hooks/`

`hooks/scripts/` is a standalone utility, unrelated to the dashboard: Windows toast notifications for
Claude Code's `Notification`/`Stop` hook events, with `Install-ClaudeHooks.ps1`/
`Uninstall-ClaudeHooks.ps1` to set them up on a machine. See `hooks/README.md` for how it works and
full install/uninstall/test steps. (The dashboard's one reach into it: `api/` runs
`scripts/Open-ClaudeRepoWindow.ps1` for the open-repo action — see `api/` above.)

`hooks/ledgerScripts/` is the exception: an **optional, dashboard-coupled** hook script, kept apart
from `scripts/` precisely because it only makes sense with this app. `Relay-PermissionRequest.ps1` is
a `PermissionRequest` hook that forwards each prompt Claude Code is about to show (permission dialog
or `AskUserQuestion`) to `POST /api/sessions/{id}/decisions` on `127.0.0.1:<port>` (`-Port`, baked in
by the installer, else `$env:LEDGER_PORT`, else 8501) and waits, so the dashboard can answer it. It
must **print nothing at all** — empty stdout, exit 0 — whenever it has no answer (backend down, no
answer in time, any error): any output is a decision, and silence leaves the terminal dialog as the
only way to answer, exactly as if the hook weren't installed. The hook is machine-wide, so it fires
for every session, not just ones the dashboard shows. It's installed separately from the toast
hooks: `Install-ClaudeHooks.ps1 -IncludeSessionControl` (add `-SkipToastHooks` for the relay alone)
copies it to `%USERPROFILE%\.claude\hooks\ledgerScripts\`, merges the `PermissionRequest` entry
(empty matcher, `timeout` 1810s — kept above the script's own 1805s wait) into `settings.json`, and
removes the legacy `PreToolUse` relay entry an earlier version of this feature installed;
`Uninstall-ClaudeHooks.ps1 -IncludeSessionControl` removes just the relay entries. Behavior was
verified against Claude Code 2.1.281 (the hook runs alongside the dialog, a late hook result is
discarded, `updatedInput.answers` answers an `AskUserQuestion`) — re-check after a Claude Code
upgrade. See `hooks/README.md` section 6.

### `openspec/`

The OpenSpec workflow directory. `openspec/specs/` holds the current, agreed specs for shipped
capabilities: `web-dashboard`, `responsive-layout`, `network-access`, `live-context-gauge`,
`toast-context-line`, `remote-session-control`. `openspec/changes/` holds proposals in flight (each with
`proposal.md`/`design.md`/`tasks.md` plus a spec delta) — currently `add-transcript-history-backup`; completed ones move to
`openspec/changes/archive/` and aren't tracked further. Treat the specs as the authoritative record
of what a capability is required to do, ahead of inferring intent from the code alone.

### Other repo files

- `api/.ledger/` (gitignored) holds the SQLite snapshot (`ledger.db*` — see "Data layer" above)
  and the LAN access token (`token`, see `api/security.py` above); both are recreated as needed and
  never committed. `.gitignore` also excludes `web/node_modules/`, `web/dist/`, and root `.env`.
- Root `.env.example` (committed) documents `BACKEND_PORT`/`FRONTEND_PORT`/`GATEWAY_PORT` in one
  place — copy it to `.env` (gitignored) to override any of them; see "Setup & Run" above for how
  each one is actually consumed.
- `api/requirements.txt`: `fastapi`, `uvicorn`, `qrcode` — unpinned. `requirements-dev.txt` adds
  `pytest`, `httpx` (for FastAPI's `TestClient`).
- `web/package.json`: React 19, `@tanstack/react-query`, `react-router-dom`, `vega-embed`
  (dependencies); Vite, TypeScript, Vitest, Testing Library, jsdom (devDependencies). `npm run build`
  is `tsc --noEmit && vite build` — a type error fails the build, not just lint.
