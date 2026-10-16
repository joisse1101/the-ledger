## 1. Backend: sign-in link and QR image

- [x] 1.1 Factor the sign-in URL and display-address logic out of `api/gateway_signin.py` so the terminal banner and the new route share it; verify `api/tests/test_gateway_signin.py` still passes unchanged
- [x] 1.2 Add an SVG QR renderer (using `qrcode`'s SVG factory, no Pillow) with a quiet zone, and verify a unit test decodes the structure and that the output has a white background
- [x] 1.3 Add a function returning `display_url` as `https://<ip>:<port>` with no token, and verify a test asserts the token never appears in it

## 2. Backend: Remote mode lifecycle

- [x] 2.1 Create `api/remote_gateway.py` with the state machine (`off`, `starting` with a step, `ready`, `failed` with a reason), all process calls injected; verify unit tests with fakes cover on, off, cancel while starting, and each failure
- [x] 2.2 Implement the steps: container runtime check and Docker Desktop launch, frontend check and start (recording that it did), gateway `docker compose up -d --build`, then a readiness poll of the gateway port; verify tests that each step is skipped when already satisfied and has a timeout
- [x] 2.3 Implement teardown: `docker compose down` always, stop the frontend only if this module started it, never stop Docker Desktop; verify tests for "started it" and "was already running"
- [x] 2.4 Wire the lifecycle to `PendingDecisions` through callbacks so the prompt gate is open only in `ready`, the 8 hour window starts at `ready`, and the lifecycle's own timer runs teardown at expiry; verify `api/tests/test_api_data.py` shows `enabled` is false while `starting` and `test_remote_gateway.py` covers expiry
- [x] 2.5 Stop a leftover gateway at backend startup; verify a test that startup calls teardown when the container exists and does not touch a running frontend
- [x] 2.6 Update `POST /api/remote-mode` to start the work in the background and return the state at once, and extend `/api/meta.remote_mode` with `state`, `step`, `reason` while keeping `enabled` and `expires_at`; verify `api/tests/test_api_data.py` covers the shape and that non-local requests still get 403
- [x] 2.7 Add `GET /api/remote-mode/qr` (local-only, 409 unless `ready`) returning `svg`, `display_url`, `expires_at`; verify `api/tests/test_security.py` shows a remote request with a valid token is refused and the body never leaks the token to it

## 3. Ledger UI

- [x] 3.1 Update `web/src/api/types.ts` and `queries.ts` for the new `remote_mode` shape and a QR query that runs only when enabled; verify `queries.test.tsx` updated
- [x] 3.2 Make `RemoteModeControl` show `starting` (with the step), `ready` and `failed` (with the reason), disable the switch while starting, and poll faster while starting; verify `RemoteModeControl.test.tsx` covers each state and the read-only view on other devices
- [x] 3.3 Add the QR button next to the switch and a modal showing the code and the address under it; verify tests that the button is disabled unless `ready`, the modal shows `display_url`, and no token text is in the DOM

## 4. Widget

- [x] 4.1 Add `getMeta`/`setRemoteMode`/`fetchQr` to `widget/src/main/api.ts` and poll `/api/meta` beside `/api/live`; verify tests with a fake server for the success, error and offline cases
- [x] 4.2 Add IPC channels (`remoteState`, `setRemote`, `ledgerHover`) in `widget/src/shared/ipc.ts` and the preload, and verify `tests/ipc.test.ts` passes (preload literals match)
- [x] 4.3 Add the header toggle with a state dot to the renderer and verify a renderer test for off, starting, ready and failed
- [x] 4.4 Create the tooltip window (`focusable: false`, ignores the mouse, no taskbar entry, same sandbox and CSP) with a small renderer page that draws a message or the QR on an opaque white card with the address and time left; verify a test that it renders each state and never shows the token
- [x] 4.5 Show the tooltip on Ledger-button hover after a short delay, hide on leave, auto-show for a few seconds when the state becomes `ready`, and place it on the side with room on the widget's display; verify unit tests for the placement function and the show/hide logic
- [x] 4.6 Confirm the widget never starts Docker or the gateway itself and the "Open Ledger" action is unchanged; verify the existing supervisor tests still pass and `npm test` and `npm run build` in `widget/` are green

## 5. Scripts

- [x] 5.1 Remove the gateway from `Start-Ledger.ps1`'s default path and add `-Remote` (calls `POST /api/remote-mode`, waits for `ready`, prints the banner); keep `-NoGateway` as an accepted no-op with a note; verify with `.\Start-Ledger.ps1` that no gateway container starts and with `-Remote` that one does
- [x] 5.2 Check `Stop-Ledger.ps1` still stops a gateway however it was started; verify by starting Remote mode from the widget then running it

## 6. Docs and end-to-end check

- [x] 6.1 Update `wiki/Backend-Live-Sessions-And-Prompts.md`, `Backend-API-Routes.md`, `Gateway.md`, `Widget.md`, `Frontend-Sessions.md` and `Setup-And-Run.md` for the new behavior; verify `cd api; python check_docs.py` passes
- [x] 6.2 Run `cd api; pytest`, `cd web; npm test; npm run build`, and `cd widget; npm test; npm run build`; verify all green
- [x] 6.3 Manual check with Docker Desktop stopped: toggle on from the widget, see the starting message, then the QR, scan it from a phone and sign in; toggle off and confirm the gateway container is gone and a frontend that was already running is still up
