## Why

Remote mode is only a flag today. The Ledger can say "on" while no gateway is running, so a phone
can't connect. The sign-in QR exists only as terminal text printed by a start script, which is easy
to lose. Turning Remote mode on from the Ledger or the desktop widget should do everything needed
for a phone to connect, and turning it off should shut all of it down.

## What Changes

- **Remote mode now means "reachable from other devices".** Turning it on starts what is needed:
  Docker Desktop if it isn't running, the frontend if it isn't up (the gateway proxies `/` to it),
  then the gateway container. It reports progress as a state (`off`, `starting`, `ready`, `failed`
  with a reason), so the switch never says "on" while nothing is listening.
- **Turning it off, or the 8 hour expiry, closes it again.** The gateway container is stopped, and
  so is the frontend, but only if Remote mode started it. A frontend that was already running is
  left alone. Docker Desktop is left running.
- **The backend does the work.** The widget and the Ledger both call the backend on loopback, so
  they share one code path and the 8 hour timer fires even if the widget isn't running. After a
  backend restart Remote mode is off, and any gateway left running is stopped at startup.
- **New local-only QR endpoint.** It returns the sign-in QR as an SVG, plus the display address
  (`https://<ip>:<port>`, no token) and the time left. It is refused for any non-local request,
  because the QR carries the access token.
- **Ledger Live list:** next to the Remote mode switch, a button opens the QR in a modal. The switch
  shows `starting` and `failed` states with the reason.
- **Desktop widget:** a Remote mode toggle in its header. Hovering the Ledger button shows a small
  tooltip window with the current state: a "Starting Docker..." or "Starting gateway..." message
  while it comes up, then the QR, the address under it (no token) and the time left. It also pops
  open on its own for a few seconds when Remote mode becomes ready.
- **`Start-Ledger.ps1` no longer starts the gateway by default.** The gateway comes up only through
  Remote mode, or with a new `-Remote` switch. **BREAKING:** a gateway that used to come up at
  launch now needs the toggle or `-Remote`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `remote-session-control`: Remote mode controls reachability as well as prompt access, has a
  starting/ready/failed state, and shuts the gateway down when it turns off or expires.
- `network-access`: the gateway is started and stopped by Remote mode; a local-only endpoint serves
  the sign-in QR; the launch script no longer starts the gateway by default.
- `web-dashboard`: the Remote mode switch shows progress and failure, and a button opens the QR in a
  modal on the machine running the app.
- `desktop-widget`: a Remote mode toggle and a QR/status tooltip window. This replaces the rule that
  the widget never touches the gateway or Docker, since it now asks the backend to.

## Impact

- **Backend (`api/`):** `pending_decisions.py` (Remote mode state), `server.py`
  (`/api/remote-mode`, `/api/meta`, a new QR route), a new module that runs Docker and the gateway
  (and the frontend) and tracks what it started, `gateway_signin.py` (reuses its address and token
  logic, adds SVG output via the existing `qrcode` dependency).
- **Frontend (`web/`):** `RemoteModeControl.tsx`, a new QR modal, the API types and queries.
- **Widget (`widget/`):** a new IPC channel and preload method, API client calls, a second small
  frameless window for the tooltip, header toggle in the renderer.
- **Scripts:** `Start-Ledger.ps1` (gateway off by default, `-Remote`), `Stop-Ledger.ps1`.
- **Docs:** `Backend-Live-Sessions-And-Prompts`, `Backend-API-Routes`, `Gateway`, `Widget`,
  `Frontend-Sessions`, `Setup-And-Run`.
- **Risk:** the QR holds the access token, so the endpoint stays local-only and the tooltip only
  draws SVG it is handed. Starting Docker Desktop is slow and can fail, so every step has a timeout
  and a visible failure state.
