## Why

The access token is a long-lived secret: it is stored in `api/.ledger/token` (or `LEDGER_TOKEN`), never
changes unless the file is deleted by hand, and a link that was shared once keeps working every time
Remote mode is turned on again. Remote mode already has a clear on/off lifecycle, so the token should
live exactly as long as one Remote session and a fresh one should be issued, with its QR code, each
time Remote mode turns on.

## What Changes

- Remote mode mints a new random token (256 bits) in memory every time it goes from off to starting.
  A start request while Remote mode is already starting or ready does not mint another.
- The token is cleared when Remote mode turns off, however that happens: the switch, the 8 hour
  expiry or a failed start. With no token, every request from another device is refused, so nothing
  is reachable even if the gateway container were left running.
- `GET /api/remote-mode/qr` keeps its contract and encodes the current session's token. There is no
  separate "generate token" endpoint and no regenerate control in the dashboard.
- A device that signed in with an earlier token is refused after Remote mode is switched back on and
  shows the existing "This device isn't signed in" state until it scans the new QR code.
- **BREAKING**: remove the stored token file `api/.ledger/token`, the `LEDGER_TOKEN` override and
  `provision_token()`. The backend no longer provisions anything at startup.
- **BREAKING**: remove the terminal sign-in banner (link and QR) printed by `gateway_signin.py`,
  `Start-Ledger.ps1 -Remote` and `gateway/Start-Gateway.ps1`. The dashboard's QR dialog is the only
  sign-in path. `gateway_signin.py` keeps only the URL helpers the backend uses.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-access`: replace "Token is set once and stays valid across restarts" with a per-session
  token; adjust "Opening a link once signs the device in" (signed in only until the session's token
  is replaced) and "Startup tells the user how to open the app" (no gateway sign-in banner);
  adjust "The sign-in code is available to the local machine as an image" (the code carries the
  token minted for this session).

## Impact

- Backend: `api/app/core/security.py` (drop `provision_token`, add a token generator),
  `api/app/deps.py`, `api/app/infra/remote_gateway.py` (start hook, clear on every path to off),
  `api/app/services/remote_service.py`, `api/app/main.py`, `api/app/cli.py`,
  `api/app/infra/gateway_signin.py` and `api/gateway_signin.py`.
- Scripts: `Start-Ledger.ps1` (drop the banner call), `gateway/Start-Gateway.ps1` (drop the banner
  call and its help text).
- Docs: `wiki/Backend-Security.md`, `wiki/Gateway.md`, `wiki/Setup-And-Run.md`,
  `wiki/Repository-Layout.md`, `wiki/Backend-Data-Layer.md`, `wiki/Testing.md`.
- Tests: `test_security.py`, `test_cli.py`, `test_main.py`, `test_gateway_signin.py`,
  `test_remote_gateway.py` and the Remote service/route tests.
- No frontend change and no API shape change: `web/src/api/token.ts` and `RemoteQrDialog` are untouched.
