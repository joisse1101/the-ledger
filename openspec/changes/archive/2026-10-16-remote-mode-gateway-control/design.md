## Context

See proposal.md for why. Today Remote mode is an in-memory flag in `PendingDecisions`
(`api/pending_decisions.py`) with an 8 hour TTL. `POST /api/remote-mode` flips it for local requests
only and `/api/meta` reports it. The gateway is a separate Docker Compose service
(`gateway/docker-compose.yml`) started by `Start-Gateway.ps1` or `Start-Ledger.ps1`, and nothing
links it to the flag. The sign-in banner and its ASCII QR live in `api/gateway_signin.py`, which
reuses `banner.discover_ipv4()` and `banner.render_qr()`; `qrcode` is already a dependency. The
widget (`widget/`) is a sandboxed Electron app that polls `GET /api/live` on loopback, starts the
backend and frontend through `Supervisor`, and by spec never touches Docker or the gateway. The
gateway proxies `/` to the frontend, so it is useless without one.

## Goals / Non-Goals

**Goals:**
- One place that brings Remote mode up and down, used identically by the Ledger, the widget and
  `Start-Ledger.ps1 -Remote`.
- The state shown to the user is true: `ready` only after the gateway answers.
- A stopped Remote mode leaves no gateway running, including after a backend crash or restart.

**Non-Goals:**
- Stopping or quitting Docker Desktop. It is only started if needed.
- Changing authentication, the token, the gateway's TLS setup or its ports.
- Letting the widget answer prompts or show them. It still only starts and stops Remote mode.
- Showing more than one QR. The first network address is used, as the banner does today.

## Decisions

**1. The backend owns the lifecycle, in a new `api/remote_gateway.py`.**
It runs the steps, records which it started, and exposes the state. The widget and the Ledger only
call `POST /api/remote-mode`. Alternatives: the widget drives Docker (rejected: the 8 hour timer
must fire when the widget isn't running, the Ledger would need its own copy, and the widget spec
keeps it a loopback-only client); a PowerShell script started by each caller (rejected: two code
paths and no structured progress).

**2. A small state machine: `off -> starting(step) -> ready`, or `-> failed(reason) -> off`.**
Steps, in order, each skipped if already satisfied: container runtime up (`docker info`, else launch
Docker Desktop and poll), frontend up (else start `npm run preview` as `Supervisor` does, and
remember it did), gateway up (`docker compose up -d --build`, then poll the gateway port over TLS
without verification, since it is self-signed). Each step has its own timeout, about 120 s for the
runtime and 60 s for the others. On any failure, undo what this run started and go to `failed` with
a short reason (`Docker Desktop is not installed`, `Docker did not start in time`, ...). `failed`
stays visible until the next toggle or a short timeout, then reads as `off` again.
The work runs in a background thread so `POST /api/remote-mode` returns immediately with `starting`;
clients poll. Turning off while `starting` cancels at the next step boundary and tears down.

**3. The flag follows the state.** `remote_mode_enabled()` (the prompt gate in
`server._can_see_prompts`) is true only in `ready`. The 8 hour TTL starts when it becomes `ready`,
not when the toggle is pressed, so a slow Docker start doesn't eat into it. Expiry is checked where
the TTL is already checked and calls the same teardown. This keeps `PendingDecisions` a plain state
store and puts process control in `remote_gateway.py`, which it calls through an injected
callback so the unit tests keep using fakes.

**4. Teardown only closes what Remote mode opened.** The module remembers whether it started the
frontend (and its pid) and stops only that. The gateway is always `docker compose down`. Docker
Desktop is never stopped. This matches the widget's existing ownership rule.

**5. Backend restart is `off`, and cleans up.** At startup the backend runs `docker compose down`
for the gateway project if the container exists, so a gateway left by a crash or an earlier backend
can't outlive the flag. A frontend started by a previous backend is not tracked and is left alone
(it may be in use; it only listens on loopback).

**6. `/api/meta.remote_mode` grows from `{enabled, expires_at}` to
`{state, step, reason, enabled, expires_at}`.** `enabled` stays for existing clients and means
`state == ready`. The widget polls `/api/meta` on its existing 2 s cadence next to `/api/live`, so no
new push channel. Alternative: a separate status route (rejected: two routes to keep in step).

**7. QR from a new `GET /api/remote-mode/qr`, local-only, 409 unless `ready`.** It returns
`{svg, display_url, expires_at}`. The SVG comes from `qrcode`'s built-in SVG factory (no Pillow),
sized with a quiet zone, black on white. `display_url` is `https://<ip>:<port>` with no token. The
full sign-in URL is built by factoring the address and token logic out of `gateway_signin.py` so the
terminal banner and this route share it. The route uses `is_local()` like the delete and Remote mode
routes; a valid token isn't enough. The SVG goes to the clients as data, and clients render it as an
`<img src="data:image/svg+xml,...">` or sanitised inline, never `innerHTML` of unknown markup.

**8. Ledger UI.** `RemoteModeControl` shows the state next to the switch (a spinner and the step
while `starting`, the reason on `failed`) and a "QR" button that opens a modal, built on the existing
`ConfirmDialog`/dialog styling. The query that fetches the QR runs only while the modal is open. The
`useSetRemoteMode` mutation no longer assumes success: it invalidates `/api/meta` and the control
reads the state from there, polling faster (about 1 s) while `starting`.

**9. Widget UI.** The renderer header gets a toggle with a state dot. The main process polls
`/api/meta` and forwards the remote state over a new IPC channel; the toggle sends a new `setRemote`
channel handled in main, which calls the backend. The tooltip is a second `BrowserWindow`: frameless,
transparent=false, always-on-top, `focusable: false`, `skipTaskbar`, `setIgnoreMouseEvents(true)`,
with its own small HTML and the same sandbox and CSP as the main one. The main window's renderer
reports hover enter and leave on the Ledger button over IPC. Main shows the tooltip after a short
delay, hides it on leave, and also shows it for about 8 seconds when the state flips to `ready`. It
places it on the side of the widget with room on the display that contains it. Content is a state
message, or the QR on an opaque white card with `display_url` and the time left under it. The QR is
fetched by main on becoming `ready` and kept in memory only. A background window with the QR is not
created until needed and is destroyed or hidden when not.

**10. `Start-Ledger.ps1`.** The gateway block is removed from the default path. A new `-Remote`
switch calls `POST /api/remote-mode` after the backend is up and waits for `ready`, then prints the
existing banner. `Stop-Ledger.ps1` keeps `docker compose down`, so it still closes a gateway however
it was started. `-NoGateway` stays accepted as a no-op for old habits, with a note.

## Risks / Trade-offs

- [Docker Desktop takes a minute or more, or never starts] -> per-step timeouts, `failed` with a
  reason, and the toggle never reports on before `ready`.
- [The QR contains the access token and is drawn on screen] -> local-only route, nothing written to
  disk, the tooltip hides on leave and after its short auto-show, and the on-screen text omits the
  token.
- [Race: toggled on then off during `starting`, or two clients toggling] -> one lock around the state
  machine, off cancels at the next step boundary and tears down, the last request wins.
- [Backend killed while Remote mode is `ready`] -> the gateway keeps running until the next backend
  start, where decision 5 stops it. Accepted: the backend is the only thing that knows to.
- [Frontend started by Remote mode is a `npm` child of the backend] -> it must be tree-killed on
  teardown and on backend exit, the same care `Supervisor` takes. If the backend dies first it is
  orphaned like the widget's own children and a later start adopts it.
- [Changing the default: the gateway no longer comes up with `Start-Ledger.ps1`] -> documented in
  `Setup-And-Run` and `Gateway`, and `-Remote` restores one-command startup.
- [The widget's hover tooltip is a second window] -> more Electron surface, kept small: no node, no
  navigation, content only from main.

## Migration Plan

No data migration. Ship the backend first, since the new `/api/meta` fields are additive and old
clients keep reading `enabled`. Then the Ledger UI, then the widget, then the script default. Rollback
is reverting the change; Remote mode returns to a plain flag and the gateway to being started by
hand, with no state to repair.

## Open Questions

- Which address to encode when the machine has several (VPN, virtual adapters). The first is used
  as today; a picker in the modal can follow if it proves wrong in practice.
- Exact auto-show duration and hover delay for the tooltip; tune by feel.
