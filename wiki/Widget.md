# Widget

> Requirements live in `openspec/specs/desktop-widget/spec.md`. This page describes how the code meets them, not what it must do.

`widget/` is a small Electron app: a frameless, always-on-top window that lists the live Claude Code
sessions with each one's context size, so the Ledger is useful without opening it. It is read-only
and Windows-only, like `hooks/`. It has its own `package.json`, imports nothing from `web/`, and is
is the only part of the repo that is not a service, a hook or a skill. Its one write is the Remote
mode switch described below.

## How it works

```text
Electron main process                      renderer (sandboxed)
  poller --GET /api/live--> backend          plain TS + HTML + CSS
  supervisor (hidden backend/frontend)       rows, pending tint, offline state
  tray, window, saved bounds   --IPC-->      window.widget (narrow preload API)
```

- **Polling.** The main process polls `GET /api/live` on `127.0.0.1:<backend port>` every 2 s
  (`widget/src/main/poller.ts`, `api.ts`), 3 s timeout. Any failure (refused, timeout, non-200,
  malformed body) becomes the offline state and clears the rows, so stale data is never shown.
  Loopback needs no token, and the widget stores none. It exposes no port of its own.
- **The renderer never calls the API.** The backend has no CORS middleware, and the renderer runs with
  `contextIsolation`, `sandbox`, no `nodeIntegration` and a strict CSP. It gets state and sends
  clicks through the preload bridge (`widget/src/preload/index.ts`). The channel names live in
  `widget/src/shared/ipc.ts`; the sandboxed preload cannot import them, so a test keeps both in step.
- **Context text is the server's.** A row shows `context.label` verbatim (for example
  `394k ▲ +2.1k ▁▂▃▅`), the string `claude_context.format_context` builds for the Live table and the
  toast, or `--` when `context` is null. The widget has no token formatter of its own.
- **Pending tint.** A row gets the `pending` class (warm background) when `pending_decision` is set,
  with no badge text. The prompt itself is never read or shown, and nothing can be approved here; answer in the terminal or the Ledger.
- **Row click** calls `POST /api/sessions/{id}/open-repo` (the toast-click action). A 404 shows a
  brief "Session ended" note and refreshes the list.
- **Branch.** `/api/live` items carry `git_branch`, looked up from `ledger.db` in `LiveSnapshot`
  (empty when unknown).

## Starting it

`widget/Start-Widget.ps1` resolves ports with the same precedence as `Start-Ledger.ps1` (parameter,
root `.env`, environment, defaults 8501/4173), runs `npm ci` on first use, rebuilds when the sources
are newer than `dist/`, and launches Electron. `Start-Widget.vbs` runs it with no console window.

```powershell
.\widget\Start-Widget.ps1                           # widget + the backend it needs
.\widget\Install-WidgetShortcut.ps1 -Desktop        # "Ledger Widget" on the desktop
.\widget\Install-WidgetShortcut.ps1 -Startup        # also start at sign-in (Startup folder)
.\widget\Uninstall-WidgetShortcut.ps1 [-Startup]    # remove both, or only autostart
```

The Startup-folder shortcut needs no elevation, shows in Windows' Startup apps list, and removing it
leaves the desktop shortcut working.

## Process ownership

The backend is started by the widget's main process (`widget/src/main/supervisor.ts`), not by the
script, so a cold start and the tray's "Start backend" share one code path.

- If `/api/meta` answers, the backend is adopted and never stopped by the widget.
- Otherwise the widget spawns `api\.venv\Scripts\python.exe server.py --port <p> --frontend-port <f>`
  hidden, with `api/` as its working directory.
- **Open Ledger** (tray or the header button) starts the frontend only if it is not already up:
  `npm run build` first if `web/dist` is missing, then `npm run preview -- --port <f>` hidden, then
  opens the browser. The widget never starts Docker or the gateway itself.
- **Quit** (tray) first turns Remote mode off if the widget started the backend (otherwise the
  gateway container would outlive it), then tree-kills (`taskkill /T /F`) only the processes the widget started. If the widget
  is killed instead of quit, its backend can be orphaned; the next launch finds it running and adopts it.

## Remote mode

The header has a Remote mode toggle. The widget only asks: it calls `POST /api/remote-mode` and reads
`remote_mode` from `/api/meta` on its poll; Docker, the frontend and the gateway are the backend's job
(see [Live sessions and prompts](Backend-Live-Sessions-And-Prompts.md)). While it starts, and when it
fails, the Ledger button's tooltip shows the step or reason; at `ready`, hovering the Ledger button shows a
small separate window (`widget/src/main/tooltipWindow.ts`, a frameless, unfocusable,
mouse-transparent, sandboxed page with a strict CSP) with the sign-in QR, the `https://` address and
the time left. The QR is fetched only while hovering and held in memory only; the token is never
shown or stored. `remoteTooltip.ts` holds the message text and placement logic.

## Window

- Last position and size persist to `widget-state.json` under Electron's `userData` and are clamped
  onto a visible display on load (`widget/src/main/state.ts`). The header's `–` collapses the window
  to a one-line pill (count and pending count) and expands it again.
- **Auto height.** The renderer measures its header, rows and note after every render and sends the
  height over IPC (`setContentHeight`); the main process resizes only the height, keeping position
  and width. It grows up to 10 rows, then the list scrolls. While collapsed the report is ignored, and
  expanding restores the last content height.
- A second launch focuses the running widget (`requestSingleInstanceLock`).
- The tray menu: Open Ledger, Start backend, Show/Hide widget, Quit. The window has no taskbar entry.
- The header has a small-sun and a big-sun button that step the background transparency (10–100%, 10% a click; big sun = more opaque) without fading the text; the value is remembered with the window position. A transparent frameless window may not be resizable by dragging on Windows.

See [Testing](Testing.md) for the suites and [Hooks](Hooks.md) for the toast the click action mirrors.
