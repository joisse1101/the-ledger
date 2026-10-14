## Context

See proposal.md for motivation. Current state that shapes the approach:

- `GET /api/live` already returns, per session, `context` (`size`, `growth`, `history`, and a
  server-built `label` such as `394k ▲ +2.1k ▁▂▃▅`) and `pending_decision`. The label is built by
  `claude_context.format_context`, the same function the Live table uses, so the widget needs no
  token formatting of its own.
- A loopback request with a `localhost`/`127.0.0.1` `Host` header needs no token. Non-GET requests
  also need `X-Requested-With: ledger`. There is no CORS middleware, so a browser-origin page cannot
  call the API cross-origin; a Node process can.
- `POST /api/sessions/{id}/open-repo` runs `hooks/scripts/Open-ClaudeRepoWindow.ps1`, the same
  action the toast click performs, and 404s when the session isn't live.
- `Start-Ledger.ps1` starts backend and frontend in visible windows and the gateway in Docker;
  ports resolve from args, then the root `.env`, then env vars, then defaults (8501/4173/8080).
- `/api/live` items carry no branch today, so this change adds `git_branch` to them (looked up from
  `ledger.db` in `LiveSnapshot`, empty when unknown). It is additive; existing clients ignore it.
- Layout rule: each top-level folder is self-contained and all Python lives in `api/`.

## Goals / Non-Goals

**Goals:**
- A tiny, always-on-top, read-only view of live sessions with the exact Live-table context figure.
- One command that brings up only the backend and the widget, hidden, and tears down only what the
  widget started.

**Non-Goals:**
- Rendering or answering prompts; any write action beyond `open-repo`.
- Reusing `web/` components or tokens, an installer or auto-update, packaging as a signed `.exe`.
- A new backend endpoint (only the one `git_branch` field above), a push channel (SSE/WebSocket), or token handling.
- Cross-platform support; this is Windows-only, like `hooks/`.

## Decisions

**1. Main process talks to the API; the renderer never does.** The Electron main process polls
`/api/live` (about every 2 s, matching the Live table's cadence in spirit) with Node `fetch`, and
pushes the result to the renderer over IPC. Alternatives: renderer `fetch` (blocked by the lack of
CORS and would need `file://` origin workarounds) or a proxy. The main-process route also lets the
renderer run with `contextIsolation`, `sandbox`, no `nodeIntegration` and a strict CSP, exposing only
a narrow preload API (`onSessions`, `openSession(id)`, `openLedger()`, `collapse()`).

**2. Render `context.label` verbatim.** Satisfies "same value, same formatting as the Live table
and toast" by construction. The sparkline comes along for free; CSS truncates it if the window is
narrow, and a later change can strip it without touching the contract. Rejected: reformatting
`size`/`growth` in the widget (a third copy of `humanise_tokens`, which the code already warns must
be kept in step with the toast hook and `web`).

**3. Plain TypeScript/HTML/CSS renderer, no framework or bundler for it.** One list, a header, an
offline state. The main process is TypeScript compiled with `tsc`; the renderer is a single
module plus CSS. Rejected: React/Vite for the widget (duplicates `web/`'s toolchain for ~100 lines of
UI) and importing from `web/src` (couples the folders, drags in dashboard CSS; decided with the user).

**4. The widget owns the processes it starts.** Main process ensures the backend: probe
`GET /api/meta` on `127.0.0.1:<BACKEND_PORT>`; if nothing answers, spawn
`api\.venv\Scripts\python.exe server.py --port <p> --frontend-port <f>` with `windowsHide: true`, cwd
`api/`, and remember the child. "Open Ledger" does the same for the frontend (`npm run build` first
only if `web/dist` is missing, then `npm run preview -- --port <f>`, with `BACKEND_PORT` in its env),
waits for the port, then `shell.openExternal`. On quit, `taskkill /PID <pid> /T /F` for each child
the widget started (tree kill, like `Stop-Ledger.ps1`); anything it merely found already running is
left alone. `Start-Widget.ps1` resolves ports (same precedence as `Start-Ledger.ps1`) into env vars
and launches Electron; the backend-ensure step lives in the main process so the tray's "Start
backend" and the cold-start path are the same code. Rejected: Start script spawns the backend (then
the widget can't tell whether it owns it, and quit semantics need a PID file); the gateway is never
started by the widget.

**5. Startup surfaces.** `Start-Widget.ps1` runs Electron from `widget/node_modules` (`npm ci` on
first run if absent). A silent `.vbs` launcher, following `Open-ClaudeRepoWindow.vbs`, avoids a
console flash. `Install-WidgetShortcut.ps1` creates a desktop `.lnk` to it (`-Desktop`), and/or a
Startup-folder `.lnk` for logon (`-Startup`); the paired uninstall removes them. Startup-folder
shortcut over a Scheduled Task: needs no elevation or task XML, is visible and removable in Windows'
Startup apps list, and the Scheduled Task's "run whether or not logged on" mode isn't wanted for a
GUI.

**6. Single instance and position.** `app.requestSingleInstanceLock()`; a second launch focuses the
first. Window bounds persist to a small JSON file under Electron's `userData`, clamped to a visible
display on load. Collapse toggles between the list and a one-line pill (count + pending marker),
kept in the same file.

**7. Click-through errors.** A row click calls `open-repo` with `X-Requested-With: ledger`. 404
shows a transient "session ended" note and triggers an immediate refresh; other failures show a
generic note. The widget never retries a click.

**8. Offline handling.** Any failed poll (connection refused, non-200, timeout 3 s) flips the state to
offline and clears rows, so stale data is never shown; polling continues and the next success restores
the list. The tray's "Start backend" runs decision 4's ensure step.

**9. Layout and docs.** `widget/` is a sixth top-level folder (`package.json`, `src/`, `tests/`,
scripts). Docs updated: `CLAUDE.md`, `Repository-Layout`, `Coding-Standards`, a new `Widget` wiki
page, `Home`, `_Sidebar`, and the `CLAUDE.md` routing table. `widget/` gets no nested `CLAUDE.md`
unless it grows rules worth one.

## Risks / Trade-offs

- [Electron adds ~100 MB of `node_modules` and a persistent process] → Accepted by the user; the
  window is idle most of the time and polling is a localhost GET.
- [Hidden backend can be orphaned if the widget is killed rather than quit] → Next launch's probe
  finds it running and adopts it as "not ours"; add an optional PID file only if this proves annoying.
- [Backend `/api/live` is 1 s-cached server-side, so rows lag by up to a few seconds] → Matches the
  Live table; the spec says "within a few seconds".
- [Always-on-top can cover fullscreen apps or games] → Tray "Hide widget" and the collapse pill;
  consider hiding on fullscreen later.
- [`context.label` contains Unicode block glyphs that need a font that has them] → Segoe UI Symbol
  fallback in CSS; verify visually since there is no UI test harness.
- [Spec says the start script starts the backend, design puts that in the main process] →
  Observable behavior is identical (backend up, no console window); the spec scenarios are tested
  end-to-end from the script.
- [Electron on first run needs network for `npm ci`] → `Start-Widget.ps1` reports a clear error and
  does not start a half-installed widget.

## Migration Plan

Additive: nothing existing changes behavior. Ship `widget/`, then run `Install-WidgetShortcut.ps1`
(`-Desktop`, optionally `-Startup`). Rollback: run the uninstall script and delete `widget/`.

## Open Questions

- Default window size and whether to hide on fullscreen apps; both are tunable without changing the
  specs.
