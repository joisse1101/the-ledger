# Backend: API routes

`api/server.py` is both the ASGI app and the CLI (`python server.py [--host] [--port]
[--frontend-port] [--reload]`, env `LEDGER_HOST`/`LEDGER_PORT`/`LEDGER_FRONTEND_PORT`; default host
`127.0.0.1` port `8501`). It always binds loopback only now — `--frontend-port` only controls the
printed frontend link, and `--lan` is still recognized by the parser but exits with an error
pointing at the gateway (`gateway/`) instead of binding `0.0.0.0`; the gateway container is the only
thing that ever grants LAN access (see [Setup and run](Setup-And-Run.md)). `--reload` (dev only, no
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
frontend is a wholly separate process (see [Frontend API layer](Frontend-Api-Layer.md)). Routes:

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
| `GET /api/overview?range=&project=&group_by=` | 422 for an unknown range label or `group_by` (`project` default, or `branch`); `project` (a path from `/api/projects`) scopes it to that project's transcripts and 404s unless it exactly matches a known project (its folder is derived server-side via `claude_db.sanitize_project_path`); otherwise `overview_stats.overview()`'s payload, whose donut/bar rows are `groups` (each keyed `group`) plus `group_order`; every response (empty or not) also carries `available_ranges`, the `TIME_RANGES` labels with at least one session in scope (the project's, when scoped), which the Projects panel uses to disable empty range buttons |

There's no static-file serving or SPA fallback here; that's `vite preview`'s job in `web/`.
`GZipMiddleware` and `SecurityMiddleware` (added first so it's outermost — nothing else runs for a
refused request) wrap every route. There is no `CORSMiddleware` at all: the frontend only ever
calls relative `/api/...` paths (`vite dev`'s proxy, `vite preview`'s proxy, or the gateway's proxy),
so no browser page is ever served from a different origin than the one it calls, and the backend
never receives a legitimate cross-origin request to allow (`test_server.py` asserts no
`CORSMiddleware` is registered).

- `api/banner.py` — what the server prints at startup: always a reminder that the frontend is a
  separate process and how to start it (`cd web && npm run preview`), plus its local URL — the
  backend has no LAN-facing state to report any more, so that's the whole banner (`build_banner()`).
  Its `discover_ipv4()` (a UDP-connect trick to find the outbound interface, plus hostname
  resolution, filtered by `usable_ipv4` to drop loopback/link-local/unspecified addresses) and
  `render_qr()` (ASCII QR via `qrcode`; `None` if the package or the terminal's encoding can't render
  it) are still here and still exercised by `test_banner.py`, but are no longer called from the
  backend's own startup path — `api/gateway_signin.py` reuses them instead (see [Gateway](Gateway.md)) to
  build the gateway's own sign-in banner/QR from the gateway side, once the gateway container starts.
