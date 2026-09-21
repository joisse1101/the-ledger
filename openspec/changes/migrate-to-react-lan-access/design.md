## Context

See proposal.md for motivation and the specs for required behavior. Constraints that shape the approach:

- All the hard logic is already plain Python and Streamlit-free: `claude_db` (scan + SQLite snapshot), `claude_sessions` (live registry), `claude_transcripts`/`claude_projects` (queries + deletes), `claude_context` (token history, attribution, sparkline text). Only `app.py` and `views/` import Streamlit. Some of `views/` is pure logic hiding inside UI modules and worth keeping: `overview.py` (time-range filter, per-project totals, hourly buckets, duration formatting), `sessions_data.py` (search/filter/sort), and the Vega-Lite specs in `overview.py` and `sessions_context.py`.
- The Live list polls every 2 s. Today that is one browser tab; with phones connected it becomes N clients, each polling, against module-level caches (`claude_sessions._cache`, `claude_context`'s memo dicts) that were written assuming one Streamlit script thread.
- `claude_db._connect()` opens a fresh SQLite connection per call and `refresh()` replaces both tables in one transaction. That was fine for one script thread; concurrent readers during a refresh need WAL and a busy timeout.
- The snapshot lives at `.streamlit/ledger.db`, a directory that this change deletes.
- Node 24 is installed locally; the repo currently has no Node tooling. The user's OS is Windows, where the first inbound bind on `0.0.0.0` triggers a Windows Defender Firewall prompt.
- Transcripts contain prompts and file contents, and the app can delete them. Anything that widens who can reach it has to be gated (see `network-access`).

## Goals / Non-Goals

**Goals:**
- One process, one port, started with one command; Python data layer unchanged apart from `db_path()` and SQLite pragmas.
- A phone can be signed in by scanning one QR code, and stays signed in.
- Behavior parity with the Streamlit app, then a clean removal of it. Streamlit stays runnable until parity is confirmed.
- The Live list stays cheap no matter how many devices are watching.

**Non-Goals:**
- No TLS/HTTPS, user accounts, roles, or per-device tokens. One shared token, plain HTTP, trusted network. The docs say so.
- No internet exposure, tunnels, or reverse-proxy support (only enough handling that a tunnel can't bypass the token by accident).
- No push updates (SSE/WebSocket). Polling matches current behavior and is simpler to secure and debug.
- No offline/PWA support, native app, or notification work (`hooks/` remains the toast path).
- No new data features. The Overview, tables, and detail view show what they show today.
- No client-side timezone handling and no `tz` request parameter: all date and hour bucketing uses the server's local timezone (see Risks).
- No prebuilt or released `dist/`: the front end is always built locally with Node.

## Decisions

**1. Keep Python for the backend: FastAPI + uvicorn wrapping the existing modules.** The API is thin: it calls `load_sessions()`, `live_context()`, `load_transcripts()`, `load_detail()`, the delete functions, and `refresh()`, and serializes their dataclasses. No parsing logic is rewritten, so the transcript-format knowledge, cost table, and 500+ lines of tested code stay where they are.
*Alternatives:* a Node backend (rejected: would re-implement jsonl parsing, the SQLite snapshot, and context attribution in a second language); keeping Streamlit and adding custom components (rejected: the layout problem is Streamlit's own column/dialog model, and there's still no auth story); Flask (fine, but FastAPI gives request validation and a typed dependency for the auth check for free).

**2. One process serves both the API and the built front end.** FastAPI mounts `web/dist` (assets with long cache lifetimes, hashed filenames) and falls back to `index.html` for any non-`/api` path so client-side routes survive a reload. During development Vite runs on its own port and proxies `/api` to 8501. Responses go through gzip middleware, since the chart chunk is the largest thing a phone downloads. If `web/dist` doesn't exist the server still starts, prints the build command, and answers page requests with a plain-text explanation (spec: startup requirement).
*Alternative:* commit or publish a prebuilt `dist/` (rejected, decided: build output stays out of git and releases; anyone running the app builds it once with `npm ci && npm run build`).

**3. API surface: coarse, read-mostly JSON, resource-oriented.**

| Endpoint | Purpose |
|---|---|
| `GET /api/live` | Live sessions, each with its context (`{size, growth, history, label}`, or null) |
| `GET /api/transcripts?q=&project=&version=&branch=&sort=&dir=&limit=&offset=` | One page of the All list + `total` + filter option lists |
| `GET /api/sessions/{id}` | Recap fields + `SessionDetail` (turns, compactions, attribution), or a `readable: false` marker |
| `DELETE /api/sessions/{id}` | Delete a transcript; 409 if the session is live, 404 if unknown |
| `GET /api/overview?range=` | Summary figures + chart-ready aggregates for the range |
| `GET /api/projects` / `DELETE /api/projects?path=` | List / delete (path passed as a query value and matched exactly against known projects) |
| `GET /api/meta` / `POST /api/refresh` | `refreshed_at`; rescan now |

The context `label` is the string from the existing `claude_context.format_context()` (`394k ▲ +2.1k ▁▂▃…`), so the humanising/sparkline rules stay in one Python place instead of a second TypeScript copy; raw numbers are sent too for later use. Detail chart data is the per-turn records, and the client builds the Vega-Lite spec.

**4. Server does the aggregation, filtering, sorting, and paging.** Overview stats are computed server-side from the same transcript rows (`overview_stats.py`, the pure functions lifted out of `views/overview.py` with the range table, calendar-date bucketing, top-7 + Other, and hourly trim intact). The All list is filtered/sorted/paged in `transcript_query.py`, a plain-Python port of `_filter_transcripts_dataframe`/`_sort_transcripts_dataframe` (literal, case-insensitive substring match; stable sort; missing values last in both directions). This keeps a phone's payload to one page (default 50) rather than the full history with 600-character snippets, and keeps the semantics in tested Python. Pandas is dropped if nothing else imports it once `views/` is gone.
*Alternative:* ship everything and filter in the browser (rejected: multi-MB first load on a phone; splits logic across two languages).

**5. React + TypeScript + Vite, with TanStack Query, React Router, plain CSS.**
- *Router:* real URLs (`/`, `/overview`, `/projects`) so reload/back/forward work, matching the spec; the server's SPA fallback supports it.
- *TanStack Query* does the polling and error behavior the spec asks for with little code: `refetchInterval: 2000` for Live, `refetchIntervalInBackground: false` (no polling while the tab is hidden) plus refetch on visibility/focus, stale data kept on error with `isError` to show an out-of-date banner, automatic recovery when the server returns. The Auto-refresh switch just sets `refetchInterval` to `false`.
- *Styling:* hand-written CSS with custom properties for theme and spacing tokens, using media queries at 640/1024 px. No component library: the layouts here (card/table switch, bottom nav, sheet) are custom anyway and a library would fight them.
- *Charts:* `vega-embed` with the existing Vega-Lite specs ported to TypeScript (donut, grouped bars, stacked token bars with cache-miss triangles and compaction rules). Re-encoding those layered marks in another library costs more than the bundle size does. The chart module is dynamically imported, so the Sessions page, which is what a phone opens first, doesn't pay for it until Overview or a detail view needs it. Specs use `width: "container"` and read colors from CSS variables at render time.
*Alternatives:* Recharts/visx (rejected as above); Tailwind/MUI (rejected: extra machinery for a small app); Next.js (rejected: no SSR need, would add a Node runtime to serve it).

**6. Responsive strategy: CSS for reflow, one hook where markup must differ.**
- A `useViewportClass()` hook (matchMedia on 640/1024) chooses between two renderers of the same list: `<table>` (medium hides columns marked low priority; wide shows all) and stacked cards (narrow). Only one is in the DOM at a time, so there aren't hidden duplicate rows. Both take the same row data and click handler, so order and selection are identical (spec: same data in every layout).
- Sorting on cards uses a "Sort by" `<select>` plus a direction button, since there are no headers.
- Nav is one component that renders as a top bar or a fixed bottom tab bar by class. Content gets bottom padding equal to the bar plus `env(safe-area-inset-bottom)`; the viewport meta uses `viewport-fit=cover`; full-height layouts use `dvh`, not `vh`, so mobile browser chrome doesn't cut them off.
- The detail view is a native `<dialog>` opened with `showModal()`: it gives Esc, focus trapping, and inert background for free. CSS turns it into a full-screen sheet under 640 px (sticky header with the close button) and a centered dialog above. It's a normal React child kept mounted while open, so the Live poll updates its props in place and its scroll position is untouched.
- Text inputs use at least 16 px font size (iOS Safari zooms on focus below that); interactive elements have a 44 px minimum hit area; KPI tiles that carry hover help are buttons that toggle an inline disclosure, so it works on tap and hover.
- Overview layout uses CSS grid with `auto-fit`/named breakpoints; charts are sized by container width and re-render on resize (`ResizeObserver`), which also handles rotation.

**7. Auth: one middleware, applied to everything.**
- *Who is local:* `request.client.host` in loopback (`127.0.0.1`, `::1`, `::ffff:127.0.0.1`) **and** none of `Forwarded`, `X-Forwarded-For`, `X-Real-IP` present. A tunnel or reverse proxy running on the same machine connects from loopback; treating forwarded requests as remote means such a setup can't silently bypass the token. Under `--lan`, opening the app via the machine's own LAN IP arrives as non-loopback and needs the token; opening it via `localhost` doesn't. That's acceptable and documented.
- *Token source:* `LEDGER_TOKEN` env var, else `.ledger/token` (created on first `--lan` run with `secrets.token_urlsafe(32)`, 256 bits). Persisted so a phone stays signed in across restarts. Compared with `hmac.compare_digest`.
- *Presenting it:* `?token=` on any URL, an `Authorization: Bearer` header, or the cookie. A valid `?token=` responds `303` to the same URL minus the token and sets `ledger_token` (`HttpOnly`, `SameSite=Lax`, `Path=/`, one-year max-age, no `Secure` since it's plain HTTP; `Lax` rather than `Strict` because a link opened from a QR scanner or another app is a cross-site navigation, and `Strict` keeps the cookie off the redirect that follows it, so the phone lands on a `401`). The redirect means the token URL is never the page in history or the address bar, so it isn't copied along with the address. A wrong token is not sign-in; it gets a `401` plain-text/HTML body pointing at the printed URL.
- *Everything is gated,* including static files, because the cookie rides along on same-origin requests and it avoids a list of exemptions to get wrong.
- *Cross-site protection:* no CORS headers are ever sent, so browsers won't expose responses to other sites; `SameSite=Lax` keeps the cookie off cross-site POST, fetch and iframe requests (only top-level GET navigations carry it, and no GET route changes anything); every non-GET request must carry a custom header (`X-Requested-With: ledger`) that the SPA adds and that forces a CORS preflight for any other origin, closing the hole that a header-less cross-site `POST /api/refresh` to an unauthenticated localhost server would otherwise leave.
- *DNS rebinding:* for loopback clients, `Host` must be `localhost`, `127.0.0.1`, or `[::1]` (any port), else `403`. Non-loopback clients are already token-gated and their Host is the LAN IP/name, so it isn't checked.
- *Logs:* uvicorn access logging is off, since it would write `?token=…` URLs to the terminal and any log file.
*Alternatives:* HTTP Basic auth (rejected: browsers re-prompt and phones can't easily use a URL/QR flow); per-device tokens (rejected as scope; the shared token is what the user chose); read-only mode for remote clients (the user chose token over this).

**8. Identifiers are validated, and the client never supplies a filesystem location.** `claude_context.transcript_path()` builds `projects_dir()/sanitize(cwd)/<session_id>.jsonl`. Exposed over HTTP, a `session_id` like `../../x` would escape that folder. The API validates `session_id` against `^[A-Za-z0-9-]{1,64}$` at the route, and resolves `cwd` server-side from the live registry or the transcripts snapshot (never from a query parameter; the Streamlit version passed `cwd` from the row). `DELETE /api/projects?path=` requires an exact match to a project in the snapshot. The existing delete functions already resolve file paths from database rows, not from request strings, and that stays.

**9. Concurrency: serialize and coalesce the live read; lock refreshes; WAL for SQLite.**
- `/api/live` is served from a `LiveSnapshot` guarded by a lock: if the last computation is under 1 s old it's returned as is, otherwise one thread recomputes (`load_sessions()` + `live_context()` per session, each session's failure isolated to `null`). N phones plus a laptop polling every 2 s cost about one recompute per second, and the non-thread-safe module caches are only touched under the lock. The transcripts endpoint takes its live-ID set from the same snapshot.
- Deletes re-read the registry fresh (not the ≤1 s snapshot) to decide whether a session is live, so a session that just started can't be deleted on a stale cache.
- `refresh()` is called under a process-wide lock from a threadpool worker (it can take seconds on a big history), whether triggered by `POST /api/refresh`, the startup call, or the 10-minute timer.
- `_connect()` sets `PRAGMA journal_mode=WAL` and a `busy_timeout` so reads during a refresh commit don't fail. `startup()` and the `atexit` hook also remove the `-wal`/`-shm` files.
*Alternative:* leave sync route handlers to FastAPI's threadpool and accept the races (rejected: `load_sessions()` mutates a dict while iterating its key set on stale entries; concurrent calls could raise).

**10. Background refresh moves into the server.** A lifespan task sleeps 10 minutes and calls the locked `refresh()` in a worker thread, in a loop, for as long as the server runs. Replaces the Streamlit fragment and its `_auto_refresh_due` bookkeeping (and its "only while a tab is open" caveat).

**11. Theme is a client concern.** `data-theme` on `<html>`, initialized from `localStorage` (guarded with try/catch) else `prefers-color-scheme`, toggled by the nav control. The categorical palette and neutral tokens from `views/overview.py` become CSS variables (light and dark sets, same slot order) that both the CSS and the chart specs read, so the palette keeps its documented fixed-order property. `.streamlit/theme_pref.json` and the process-wide `st_config.set_option` hack disappear.

**12. Entry point and LAN startup.** `server.py` is both the ASGI app and the CLI: `python server.py [--lan] [--host H] [--port P]` (env `LEDGER_HOST`/`LEDGER_PORT` as defaults). Default host `127.0.0.1`; `--lan` means `0.0.0.0`. On start it prints the local URL; with `--lan` it discovers the machine's IPv4 addresses (hostname resolution plus the UDP-connect trick to find the primary interface, without sending packets; drops loopback and 169.254.x.x), prints `http://<ip>:<port>/?token=<token>` for each, an ASCII QR of the first via `qrcode`, and the plain-HTTP warning. The first `--lan` run on Windows will pop the firewall prompt; the README says to allow Private networks and gives the `netsh` alternative.

**13. Data location.** `claude_db.db_path()` → `.ledger/ledger.db`; the token file sits beside it; `.gitignore` gets `.ledger/`, `web/node_modules/`, `web/dist/`, and loses the `.streamlit/*` lines. Existing behavior (wipe and rebuild on start, best-effort delete on exit) is unchanged.

**14. Testing.**
- Python: pytest as today, plus API tests with FastAPI's `TestClient` (needs `httpx`). Remote clients are simulated with `TestClient(app, client=("192.168.1.50", 5000))`; forwarded-header and Host cases are plain header tests. Ported: `test_overview.py` → `overview_stats`; the filter/sort cases of `test_views.py` → `transcript_query`; new: auth matrix, token persistence, id validation, delete-live-409, coalescing (recompute count), missing-`dist` behavior. `tests/test_app.py` goes with `_auto_refresh_due`.
- Front end: Vitest for pure helpers (view-class selection, URL/state helpers). Layout behavior is verified by resizing a real browser to 320/390/768/1280 px (Chrome via the browser tools) and on an actual phone over the LAN; the tasks name those checks explicitly. No Playwright harness in this change.

## Risks / Trade-offs

- [Token travels over plain HTTP, so anyone able to sniff the LAN can read it and the transcript data] → LAN mode is opt-in, the startup banner and README say it's for trusted networks only, the token is not logged, and it's a shared secret that's easy to rotate by deleting the file.
- [The token is visible in the terminal, its scrollback, and the QR] → Accepted for a single-user local tool; rotate if shared.
- [Windows Firewall silently blocks the phone] → README calls this out with the exact prompt to accept (Private network) and a `netsh` command; the startup banner reminds the user.
- [Rebuilding three pages risks losing small behaviors] → The `web-dashboard` spec enumerates the current behavior, and Streamlit is only removed in the last task group after a side-by-side check against the same data.
- [Vega-Embed adds a few hundred KB to the bundle] → Dynamic import (Sessions page doesn't load it), gzip, hashed long-cache assets; acceptable on a LAN.
- [`vh`/safe-area/`dialog` behavior differs on iOS Safari vs Chrome] → Use `dvh` and `env(safe-area-inset-*)`, keep body scroll lock simple, and check on a real phone before calling the responsive tasks done.
- [Time-range and hourly bucketing use the server's local timezone, so a device in another timezone sees the server's "today"] → Accepted: same as today's single-machine behavior and normally identical on a home network. There is deliberately no `tz` parameter.
- [Two UIs during the transition] → Only until the final task group removes Streamlit; no shared state between them, and the SQLite path change happens in that group too, so both use the old path until then.
- [The 1 s live coalescing makes Live up to 1 s staler for some clients] → Below the 2 s poll interval, so not perceptible; deletes bypass it.
- [Node is now needed to build] → One `npm ci && npm run build` step in the README; the server explains it if missing.
- [Sparkline glyph rendering differs by phone font] → Block glyphs are widely covered; if one renders badly the raw `history` numbers are already in the payload for an SVG fallback later.

## Migration Plan

1. Build the API and the `web/` app next to the existing Streamlit app, which keeps running unchanged on the old `.streamlit/ledger.db` path.
2. Compare every page against the Streamlit app on the same data, then do the LAN/phone checks.
3. In one final group of tasks: move the DB path to `.ledger/`, delete `app.py`, `views/`, `.streamlit/`, Streamlit-only tests and dependencies, update `.gitignore`, `CLAUDE.md`, and `README.md`.
4. Rollback: revert the final removal commit to get Streamlit back; the API and `web/` are additive. The SQLite file is a disposable cache, so no data migration is needed either way. Users delete the old `.streamlit/` leftovers by hand (`theme_pref.json` etc. are untracked).

## Open Questions

None. The two earlier questions (shipping a prebuilt `dist/`, and a `tz` parameter on `/api/overview`) were decided against and moved to Non-Goals.
