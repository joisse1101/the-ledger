# Backend: API routes

This page lists every `/api/*` route the backend serves, and explains the app, its command line and the rules shared by all routes. Read it to learn what a route takes and returns, and which routes only a local request may use.

A local request is one made from the machine running the app. The exact test is in [Security](Security.md).

## The app

### Entry points

`api/app/main.py` is the ASGI app: the middleware, `lifespan`, and one router per file in `api/app/routers/`. `api/app/cli.py` is the command line. Run it as a module from `api/` (`python -m app`), so that `app` is importable.

### Command line

The form is `python -m app [--host] [--port] [--frontend-port] [--reload]`. The environment variables are `LEDGER_HOST`, `LEDGER_PORT` and `LEDGER_FRONTEND_PORT`. The default host is `127.0.0.1` and the default port is `8501`.

It always binds loopback only now. `--frontend-port` only controls the printed frontend link.

`--lan` is still recognized by the parser. `--lan` exits with an error that points at the gateway (`gateway/`) instead of binding `0.0.0.0`. The gateway container is the only thing that ever grants LAN access. See [Setup and run](../Contributing/Setup-And-Run.md).

### Reload (dev only)

`--reload` has no environment variable. It restarts the process on any saved change under `api/`. It hands uvicorn the import string `"app.main:app"` instead of the already-built `app` object. Only the string form lets uvicorn re-import the module fresh per restart.

That is also why `lifespan` builds Remote mode's lifecycle when `main()` has not. The reload subprocess re-imports the module without ever calling `main()`.

### What a route handler does

A route handler only parses the request. It calls a function in `api/app/services/`. It shapes the response with `api/app/schemas/`.

The services raise the domain errors in `api/app/services/errors.py`. `api/app/routers/errors.py` turns them into 403, 404, 409, 422, 500, 503 or 507.

### Startup and refresh (`lifespan`)

`lifespan` calls `snapshot.startup()` in a worker thread on start. It runs a 10-minute `refresh_loop()` for as long as the process is up. Both go through a process-wide `refresh.lock` (`api/app/refresh.py`). `POST /api/refresh` shares that lock. So a scan, which can take seconds on a big history, is never triggered twice at once.

### What it serves

It serves `/api/*` only: no HTML, no static assets. The frontend is a wholly separate process. See [Frontend API layer](../Frontend/Api-Layer.md). There is no static-file serving or SPA fallback here; that is `vite preview`'s job in `web/`.

## Middleware

`GZipMiddleware` and `SecurityMiddleware` wrap every route. `SecurityMiddleware` is added first, so it is outermost: nothing else runs for a refused request.

There is no `CORSMiddleware` at all. The frontend only ever calls relative `/api/...` paths. Those go through `vite dev`'s proxy, `vite preview`'s proxy, or the gateway's proxy. So no browser page is ever served from a different origin than the one it calls. The backend never receives a legitimate cross-origin request to allow. `test_main.py` asserts no `CORSMiddleware` is registered.

## Routes

### Meta and Remote mode

#### `GET /api/meta`

Returns `{refreshed_at, is_local, remote_mode: {enabled, expires_at, state, step, reason}, relay_hook_seen}`. `state` is `off`, `starting`, `ready` or `failed`.

`relay_hook_seen` is true once any prompt has been relayed since the backend started. Auto-approve controls wait for `relay_hook_seen`.

`is_local` is `security.is_local(request)` for this request. So the frontend can hide controls a remote device cannot use.

#### `POST /api/remote-mode`

Body is `{enabled}`. Local requests only: 403 otherwise, token or not. It starts or stops the whole of Remote mode: Docker, frontend and gateway.

Turning it on makes this session's access token. Turning it off discards the token. It returns at once with the new `remote_mode`. Clients follow that in `/api/meta` while it is `starting`.

#### `GET /api/remote-mode/qr`

Returns `{svg, display_url, expires_at}`. It is the sign-in QR. The QR encodes this Remote session's token; `display_url` does not. Local only. 409 unless Remote mode is `ready`.

#### `POST /api/refresh`

It drops the cached repo lookups, so the next `GET /api/projects/repos` re-reads `gh`. It forces a `locked_refresh()`. It returns the new `refreshed_at`.

### Live sessions and prompts

#### `GET /api/live`

Returns `{sessions: [...]}` from the shared `LiveSnapshot` (see `live_snapshot.py`). It sweeps stale prompts first. Each session carries and gains these fields:

- `git_branch`, from `ledger.db`, `""` when unknown.
- `compact: {state, since} | null`.
  - `ok` is under 45 minutes, `should` is 45-55, `needs` is beyond.
  - It is measured from the later of `started_at` and the last compaction.
  - `since` is that moment in UTC.
  - It is `null` without a start time.
- `pending_decision: {id, tool_name, tool_input} | null`.
  - That is its oldest pending prompt.
  - It is always `null` for a non-local request while Remote mode is off.
- `auto_approve: bool`.
- `last_auto_approved: {tool_name, at} | null`.

The last two are visible to every client.

#### `POST /api/sessions/{id}/auto-approve`

Body is `{enabled}`. Local requests only: 403 otherwise, token or not. 404 unless the session is live. Returns `{auto_approve}`.

Turning it on also approves the session's already-pending plain prompts. See [Live sessions and prompts](Live-Sessions-And-Prompts.md).

#### `GET /api/sessions/{id}/pending-decision`

Returns `{pending_decision}`. It follows the same visibility rule as `/api/live`. The Live control view polls it.

#### `POST /api/sessions/{id}/decisions`

Relay hook only: local requests only, 403 otherwise. Body is `{tool_name, tool_input}`. It registers the prompt and holds the request open until the prompt is answered, cleared or times out.

It then returns `{decision: "allow" | "deny" | "answer" | null, ...}`. `null` means "no answer", and the hook then prints nothing.

#### `POST /api/sessions/{id}/decisions/{prompt_id}/answer`

It is the dashboard's answer. The body is one of:

- `{decision: "allow"}`
- `{decision: "deny", reason?}`
- `{decision: "answer", answers: {"<question>": string | string[]}}`

It fails in three ways:

- 403 for a non-local request unless Remote mode is on.
- 409 if the prompt is gone (answered or cleared elsewhere).
- 422 if the shape does not fit the prompt kind. For 422: answers must cover exactly the questions asked, and lists are only for multi-select.

#### `POST /api/sessions/{id}/open-repo`

It opens the session's `cwd` in VS Code on the host. The `cwd` comes from the live registry, never a request parameter. 404 unless the session is live. Token-gated like any other non-GET. It has no Remote-mode or locality requirement.

### Transcripts and sessions

#### `GET /api/transcripts`

Parameters are `q`, `project[]`, `version[]`, `branch[]`, `worktree[]`, `sort`, `dir`, `limit` and `offset`. It returns paged items, `total`, and the filter `options`, via `transcript_query.py`. Each item's `live` flag comes from the same `LiveSnapshot`'s live-ID set.

#### `GET /api/sessions/{id}`

Returns the recap plus `SessionDetail` JSON. `SessionDetail` holds turns, compactions, attribution, and `breakdown`. `breakdown` is `snapshots` of estimated startup categories, plus per-response `turns` of growth by tool and a remainder. `breakdown` can be `null`. Otherwise it returns `readable: false`.

`id` is validated against `^[A-Za-z0-9-]{1,64}$` at the route. `cwd` is resolved server-side from the live registry or the transcripts snapshot. `cwd` is never a request parameter.

#### `DELETE /api/sessions/{id}`

Local requests only: 403 otherwise. A valid token does not authorize a delete.

409 if `live.is_live_now(id)`. That is a fresh registry read, not the snapshot that is up to 1 second old. So a session that just started cannot be deleted on stale data.

404 if unknown. Otherwise it calls `claude_transcripts.delete_transcript` under the refresh lock.

### Projects

#### `GET /api/projects`

Returns `{projects: [...]}`.

#### `GET /api/projects/repos`

Returns `{repos: [{path, host, url, issues, prs}]}`, one per known project. Every field after `path` is `null` when unknown. Unknown means no `origin`, not a GitHub repo, or `gh` missing or signed out.

It takes no parameters. So `git` and `gh` only ever run in the known projects' folders. The code is `api/app/services/project_repo_service.py`, via `api/app/infra/repo_cli.py`. It is cached per project for 5 minutes, or 1 minute when incomplete.

#### `DELETE /api/projects?path=`

Local requests only, like the session delete. 404 unless `path` exactly matches a known project. Then it runs `delete_project` and `delete_project_transcripts`.

### Files (the drop folder)

Every `/api/files*` route is 403 while Remote mode is off, local requests included (`_require_file_drop`).

#### `GET /api/files`

Returns `{files: [{name, size, modified}]}` for the drop folder, newest first.

#### `PUT /api/files?name=`

The raw request body is streamed to disk (`file_drop.save_async_stream`). It never overwrites: it adds a ` (1)` or ` (2)` suffix. No partial file is left after a failure. 507 when the disk is full.

#### `GET /api/files/{name}`

Returns the file as an attachment, with range requests. It needs the bearer token like any other non-local request.

#### `POST /api/files/{name}/download-link`

Returns `{url}` for a single-use, 60 second link to that one file. 404 if the file is not there. A browser download cannot send the bearer header, so the page asks here first.

#### `GET /api/files/download/{ticket}`

It redeems the link and streams the file, `no-store`. 403 for an unknown, used or expired ticket. It is the one request that needs no bearer token. `security.py` matches this path shape only; the ticket is the credential.

#### `DELETE /api/files/{name}`

Local requests only, like the other deletes.

#### The drop folder itself

The folder is `api/.ledger/transfer/` (gitignored), or `LEDGER_TRANSFER_DIR` if set. Its logic lives in `api/app/infra/file_drop.py`, which has no web imports. That module also holds `DownloadTickets`.

The routes never accept a path, only a bare file name. They log `file_drop op=... name=...` lines without contents or tickets.

### Settings

Every settings route is local requests only: 403 otherwise, token or not. The desktop widget reads settings over loopback.

#### `GET /api/settings`

Returns `{worktree_folders: [{path, built_in}], widget: {max_projects, afk_minutes, break_minutes}}`.

- `worktree_folders` lists `.claude/worktrees` first (`built_in: true`), then the user's folders. <!-- docs-check: ignore -->
- `max_projects` is how many projects the desktop widget's Ledger-button tooltip lists. It is 5 until set.
- `afk_minutes` is how many minutes the widget's AFK switch stays on. It is 30 until set.
- `break_minutes` is how many minutes of work pass before the widget's break window opens. It is 60 until set.

#### `PUT /api/settings`

Body is `{worktree_folders?: [...], widget?: {max_projects?: n, afk_minutes?: n, break_minutes?: n}}`. A part left out stays as it was. Local requests only.

Everything is validated before anything is saved, so one bad value saves nothing. Each folder is normalised (`normalize_folder` in `api/app/core/worktrees.py`). These are a 422 whose `detail` says why:

- an absolute path
- a `.` or `..` part
- a blank entry
- a duplicate, including the built-in one

Each number has its own range check:

- `max_projects` must be a whole number from 1 to 10 (`validate_max_projects` in `api/app/core/widget_settings.py`), else a 422 likewise.
- `afk_minutes` must be a whole number from 1 to 240 (`validate_afk_minutes`), else a 422.
- `break_minutes` must be a whole number from 1 to 240 (`validate_break_minutes`), else a 422.

When the settings file exists but cannot be read, nothing is saved and the route returns a 500 whose `detail` names the file, so the user can fix or delete it. Saving folders runs `history.correct_worktree_rows()` and then `refresh()`, under the refresh lock. Saving any of the numbers does neither. It returns the same shape as `GET`, so the next read already reflects it.

### Widget workouts

#### `POST /api/widget/workouts/open`

No body. Local requests only: 403 otherwise, token or not. It creates `widget/workouts/mine` under the repo root if missing. It opens that folder in the file manager (`api/app/infra/folder_opener.py`; tests pass a fake opener). It returns `{path}`.

If the folder cannot be created or opened it is a 500 whose `detail` holds the path, so the page can show it. The route takes no path, so it can open only that one folder. The widget builds the same relative path itself. <!-- docs-check: ignore -->

### Overview

#### `GET /api/overview?range=&project=&group_by=`

422 for an unknown range label or `group_by`. `group_by` is `project` (default), `branch`, or `worktree`. `worktree` groups by `wt <name>` for a worktree session, and by the branch otherwise.

`project` is a path from `/api/projects`. It scopes the result to that project's transcripts. It is 404 unless it exactly matches a known project. Its folder is derived server-side via `paths.sanitize_project_path`.

Otherwise it returns `overview_stats.overview()`'s payload. The donut and bar rows are `groups`, each keyed `group`, plus `group_order`.

Every response, empty or not, also carries `available_ranges`. `available_ranges` is the `TIME_RANGES` labels with at least one session in scope (the project's, when scoped). The Projects panel uses it to disable empty range buttons.

## Startup banner

`api/app/infra/banner.py` is what the server prints at startup. It always prints a reminder that the frontend is a separate process and how to start it (`cd web && npm run preview`). It also prints the frontend's local URL. The backend has no LAN-facing state to report any more, so that is the whole banner (`build_banner()`).

### Helpers no longer used at startup

`discover_ipv4()` finds the outbound interface with a UDP-connect trick, plus hostname resolution. `usable_ipv4` filters out loopback, link-local and unspecified addresses. It now feeds the sign-in address (see [Gateway](../Services/Gateway.md)).

`render_qr()` makes an ASCII QR via `qrcode`. It returns `None` if the package or the terminal's encoding cannot render it.

Both are still here and still exercised by `test_banner.py`. Neither is called from the backend's own startup path any more. `render_qr_svg()` is the same code as an SVG, for `GET /api/remote-mode/qr`.
