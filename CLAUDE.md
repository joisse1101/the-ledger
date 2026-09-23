# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A dashboard for viewing your local Claude Code sessions and projects: Overview, Sessions (Live +
All), Projects. It's an API-only FastAPI backend (`api/`) plus one React + Vite frontend (`web/`),
built so a phone or other device on the same network can read it too, behind a shared access token
— something the project's original Streamlit UI (now retired) had no safe way to do. The backend
and frontend run as two separate processes/ports; the API never serves any HTML itself (see
"Setup & Run" below).

This started as a migration from a Streamlit app to this React+FastAPI stack; that migration is
now complete and Streamlit has been fully removed. Its rationale, decisions, and the cutover
checklist are recorded in `openspec/changes/migrate-to-react-lan-access/` (`proposal.md` for
why/what, `design.md` for the decisions, `tasks.md` for the checklist) — worth checking for the
*why* behind a design choice (e.g. why auth is bearer-token-only, why the API and frontend are
separate origins) ahead of inferring it from the code alone.

The API and frontend both read the same on-disk Claude Code data (`~/.claude.json` and
`~/.claude/projects/*/*.jsonl`) via a SQLite snapshot at `.ledger/ledger.db` (gitignored, rebuilt
from disk on every server start and periodically thereafter — see "Shared data layer" below).

## Setup & Run

Create/activate the venv and install Python dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

A `.venv` already exists at the repo root with dependencies installed — activate it
(`.venv\Scripts\Activate.ps1`, or invoke `.venv\Scripts\python.exe` / `.venv\Scripts\pytest.exe`
directly) rather than searching for or recreating one.

The frontend needs Node.js in addition to the Python setup above. It's built once (`npm run build`)
and then served by `vite preview`, which serves only the already-built `web/dist` — it doesn't
rebuild on save. `npm run dev` (hot-reloading, proxies `/api` to the backend) is available instead
while actively working on the frontend, but isn't what's used for normal local use.

**Two processes, two ports, every time** — the API only ever serves `/api/*`; the frontend is
always its own separate process:

```powershell
# Terminal 1, from the repo root: the API (defaults to http://localhost:8501)
python api/server.py

# Terminal 2, in web/: build once, then serve the built frontend (defaults to http://localhost:4173)
cd web
npm ci
npm run build
npm run preview
```

Open the frontend's URL (http://localhost:4173 by default), not the API's — the API has no page to
show you.

**From another device on your network** (phone, tablet, another computer): pass `--lan` to the API
and `-- --host` to the frontend's preview command — both must be running:

```powershell
python api/server.py --lan
```

```powershell
cd web
npm run preview -- --host
```

`--lan` binds the API to every network interface instead of just this machine; it then prints the
frontend's URL for each discovered address, a QR code, and a one-time access token — opening that
link signs the device in (the token is stored in that browser's `localStorage` and stripped from
the address bar) and every subsequent API request from it carries `Authorization: Bearer <token>`.
A local request (from this machine, via `localhost`/`127.0.0.1`) needs no token at all; every other
request needs it, checked by `api/security.py`'s `SecurityMiddleware` (see "Architecture" below).
Only do this on a network you trust: the connection is plain HTTP, so the token and your session
data aren't encrypted in transit. Windows will prompt to allow Python through the firewall the
first time — allow it on Private networks — and the same device also needs to reach the frontend's
port, not just the API's.

To rotate the access token (e.g. after sharing it), delete `.ledger/token` and restart the API; a
fresh one is generated on the next `--lan` run. Setting `LEDGER_TOKEN` in the environment overrides
the stored file entirely.

`--host`/`--port`/`--frontend-port` (or the `LEDGER_HOST`/`LEDGER_PORT`/`LEDGER_FRONTEND_PORT` env
vars) override the API's bind address/port and the port it expects the frontend on — keep
`--frontend-port` in sync with whatever port you actually run `npm run preview` on, since it's also
what the API's CORS allow-list is built from (see "Architecture" below).

Dark/light theme is chosen per device, not shared server-side: each browser picks up
`prefers-color-scheme` until it toggles the switch itself, then remembers that choice in its own
`localStorage` (see `web/src/theme/theme.ts`).

## Testing

```powershell
pip install -r requirements-dev.txt  # requirements.txt + pytest + httpx
pytest
```

`pyproject.toml` sets `pythonpath = [".", "api"]` (so bare imports like `import server` work under
pytest the same way `api/server.py`'s own `sys.path` bootstrap makes them work at runtime) and
`testpaths = ["tests"]`.

Python tests, one file per module under test:
- Shared data layer: `test_claude_db.py`, `test_claude_projects.py`, `test_claude_transcripts.py`,
  `test_claude_sessions.py`, `test_claude_context.py`. `tests/conftest.py`'s `isolated_db` fixture
  monkeypatches `claude_db.db_path`/`config_path`/`projects_dir` to a `tmp_path`, so the suite never
  touches the real `~/.claude.json` or `~/.claude/projects/`.
- API/backend: `test_server.py` (the FastAPI app's lifespan/refresh wiring, CORS allow-list), 
  `test_security.py` (the auth middleware — local vs. remote, bearer-token matching, CSRF header,
  Host rebinding-guard), `test_banner.py` (address discovery, QR rendering, banner text), `test_cli.py`
  (`parse_settings`/`main` — host/port/frontend-port precedence, token provisioning on launch),
  `test_live_snapshot.py` (`LiveSnapshot`'s TTL coalescing and per-session failure isolation),
  `test_overview_stats.py` and `test_transcript_query.py` (the pure aggregation/filter/sort logic
  behind Overview and the All list), `test_api_data.py` (the `/api/live`, `/api/transcripts`,
  `/api/sessions/{id}`, `/api/projects`, `/api/overview` routes end to end via `TestClient`).

Frontend (`cd web`):

```powershell
npm test          # Vitest: client.test.ts, queries.test.tsx, useDebouncedValue/useViewportClass
                   # tests, format.test.ts, tokens.test.ts (jsdom, see web/src/test-setup.ts)
npm run build      # tsc --noEmit, then vite build -> web/dist
```

There is no browser-automation/E2E harness for the React app; responsive layout across breakpoints
was verified manually (resizing a real browser, and a real phone over `--lan`) per
`openspec/changes/migrate-to-react-lan-access/tasks.md`'s groups 9–10.

## Architecture

### Shared data layer (repo root)

These modules are plain Python with no FastAPI/Starlette dependency of their own, read by `api/`,
and deliberately stay at the repo root rather than moving under `api/` (or a new shared package —
considered and rejected) since there's now only the one consumer but the split still keeps the pure
data layer testable and readable independent of the web framework wrapping it.

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
  handler to delete it again on exit (best-effort). `db_path()` returns `.ledger/ledger.db` (gitignored;
  `.ledger/` is also where the LAN access token lives — see `api/security.py` below).
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

`api/server.py` is both the ASGI app and the CLI (`python server.py [--lan] [--host] [--port]
[--frontend-port]`, env `LEDGER_HOST`/`LEDGER_PORT`/`LEDGER_FRONTEND_PORT`; default host
`127.0.0.1` port `8501`, `--lan` binds `0.0.0.0`). It lives one level below the repo root alongside
its own supporting modules, so it inserts the repo root onto `sys.path` before importing the
root-level modules. Its `lifespan` calls `claude_db.startup()` in a worker thread on start and runs
a 10-minute `refresh_loop()` for as long as the process is up, both funneled through a process-wide
`_refresh_lock` shared with `POST /api/refresh` so a scan (which can take seconds on a big history)
is never triggered twice concurrently. It serves `/api/*` only — no HTML, no static assets; the
frontend is a wholly separate process (see `web/` below). Routes:

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

It serves `/api/*` only — no static files, no SPA fallback; that all lives in `web/` now, served by
Vite's own `vite preview` (see below and design.md Decision 2/9). `GZipMiddleware`, `SecurityMiddleware`
(added first so it's outermost — nothing else runs for a refused request), and `CORSMiddleware`
(added last, so it's innermost — it answers a CORS preflight itself before the token/CSRF checks
above ever see it, but a real cross-origin request still has to pass them) wrap every route.
`cors_origins()`/`configure_cors()` build the exact allow-list from `--frontend-port` plus any LAN
addresses discovered under `--lan` — never a wildcard, and never a credentialed response
(`allow_credentials=False`), since auth is a bearer header, not a cookie.

- `api/security.py` — one ASGI middleware gating every request (see also `design.md`'s "Auth" decision).
  A request is **local** only when `request.client.host` is loopback (`127.0.0.1`/`::1`/
  `::ffff:127.0.0.1`) *and* carries none of `Forwarded`/`X-Forwarded-For`/`X-Real-IP` (so a tunnel or
  reverse proxy on the same machine is treated as remote, not silently trusted); local requests must
  still present `Host: localhost`/`127.0.0.1`/`[::1]` (any port) or get a 403 — this stops a public DNS
  name that resolves to 127.0.0.1 from reaching the app unauthenticated. Every non-local request needs
  the access token as `Authorization: Bearer <token>` (`hmac.compare_digest` comparison) or gets a 401
  with a message pointing back at the printed sign-in link — there is no `?token=` query handling or
  cookie on the API side at all; turning a printed link's `?token=` into that header is entirely the
  frontend's job (see `web/src/api/token.ts` below). Every non-GET request additionally needs an
  `X-Requested-With: ledger` header — a page on another site can't add a custom header without
  triggering a CORS preflight, which `server.py`'s `CORSMiddleware` only ever grants to the frontend's
  own origin(s), so that header is what stops a blind cross-site `POST`/`DELETE` even from a page that
  is otherwise allowed to read the API. `provision_token()` is `LEDGER_TOKEN` if set, else the token
  stored at `.ledger/token` (created with `secrets.token_urlsafe(32)` on first `--lan` run, mode
  `0o600`) — delete that file and restart to rotate it.
- `api/banner.py` — what the server prints at startup: always a reminder that the frontend is a
  separate process and how to start it (`cd web && npm run preview [-- --host]`), plus its local URL.
  With `--lan`, `discover_ipv4()` (a UDP-connect trick to find the outbound interface, plus hostname
  resolution, filtered by `usable_ipv4` to drop loopback/link-local/unspecified addresses) drives one
  `http://<ip>:<frontend-port>/?token=<token>` line per address plus an ASCII QR (`render_qr`, via
  `qrcode`; `None` if the package or the terminal's encoding can't render it) for the first address,
  and a plain-HTTP/trusted-networks/firewall warning.
- `api/live_snapshot.py` — `LiveSnapshot`, a lock-guarded, TTL-coalesced (`LIVE_TTL_SECONDS = 1.0`)
  wrapper around `claude_sessions.load_sessions()` + `claude_context.live_context()` per session, so
  N browsers/phones polling `/api/live` every ~2s cost about one recompute per second rather than N —
  those two modules' own caches assume a single caller, so every read of them from the API goes
  through this one lock. One session's `live_context()` raising leaves the others populated
  (`context: null` for that one). `is_live_now()` bypasses the TTL for delete decisions (see the
  `DELETE /api/sessions/{id}` route above); `cwd_for()` is used server-side only, never sent to a
  client.
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
  including the 8-slot categorical palette (`--cat-0`..`--cat-7`) and `--muted-ink`, at a fixed slot
  order so a chart's `chartColors()`/`themeColors()` (see below) never has to duplicate a hex value.
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
  shows the recap block only when opened `from="all"`; its `Detail` section (current-context figure,
  `TokensChart`, "All responses" table, "what filled the context" by-tool/largest-increases tables)
  and `DeleteControls` (confirm/cancel → `useDeleteSession`, disabled with a note when live, a 409
  mid-confirm surfaces the server's message) round it out. `TokensChart` lazily `import()`s
  `vega-embed` (so the Sessions page, the first thing a phone opens, doesn't pay for its bundle cost
  until a detail view needs it) and rebuilds/re-embeds its spec whenever the turns or the theme
  change; its spec draws the stacked Cache read/Cache written/New bars with ▼ cache-miss markers and
  dashed compaction rules.
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
  path before Confirm/Cancel. Confirming calls `useDeleteProject`, whose `onSuccess` already
  invalidates the `projects`, `transcripts`, and `overview` queries.
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

- `.ledger/` (gitignored) holds the SQLite snapshot (`ledger.db*` — see "Shared data layer" above)
  and the LAN access token (`token`, see `api/security.py` above); both are recreated as needed and
  never committed. `.gitignore` also excludes `web/node_modules/` and `web/dist/`.
- `requirements.txt`: `fastapi`, `uvicorn`, `qrcode` — unpinned. `requirements-dev.txt` adds
  `pytest`, `httpx` (for FastAPI's `TestClient`).
- `web/package.json`: React 19, `@tanstack/react-query`, `react-router-dom`, `vega-embed`
  (dependencies); Vite, TypeScript, Vitest, Testing Library, jsdom (devDependencies). `npm run build`
  is `tsc --noEmit && vite build` — a type error fails the build, not just lint.
