## 1. Token lifecycle in the backend

- [x] 1.1 In `api/app/core/security.py` replace `provision_token`, `LEDGER_DIR` and `TOKEN_ENV` with `new_token()` returning `secrets.token_urlsafe(32)`; update the module docstring. Verify in `api/tests/core/test_security.py` that two calls differ, the result is at least 43 characters, and no file is written (rewrite the provisioning tests, drop the env/file/`git check-ignore` ones).
- [x] 1.2 Add an `on_start` callback to `RemoteGateway` (`api/app/infra/remote_gateway.py`), called inside `start()` under the lock only when it leaves off/failed for starting. Verify in `api/tests/infra/test_remote_gateway.py` that it fires once for off to starting and not for a second `start()` while starting or ready.
- [x] 1.3 Make `stop()` call `on_off` under the lock right after setting off (before `_teardown()`), and make `_fail` call it when its generation is still current. Verify in `test_remote_gateway.py` that `on_off` runs on a manual stop, on the expiry timer, and on a failed start, and that a start/stop/start sequence ends with the second session's token intact.
- [x] 1.4 In `api/app/deps.py` wire `make_remote` so `on_start` sets `access_token = new_token()` and `on_off` also sets it to `None`; update the `access_token` comment. Verify with a service-level test that switching Remote mode on makes the token non-empty, off clears it, and on again yields a different value.
- [x] 1.5 Remove the `provision_token()` calls and the `--reload` explanation from `api/app/cli.py` and `api/app/main.py` (`lifespan`). Verify `api/tests/test_cli.py` and `test_main.py` assert `deps.access_token` stays `None` after startup, and that the reload branch still passes ports through env vars.

## 2. Sign-in code and banner removal

- [x] 2.1 Update `api/app/services/remote_service.py` `sign_in_code` so a missing token returns the existing 409 "Remote mode is not ready" rather than a misleading address message. Verify with route tests: ready returns a code that differs between two Remote sessions, off or starting returns 409 with no code.
- [x] 2.2 Cut `api/app/infra/gateway_signin.py` down to `signin_url` and `display_url`, and delete `api/gateway_signin.py`. Verify `api/tests/infra/test_gateway_signin.py` covers only the two helpers and `pytest` has no import of the removed names.
- [x] 2.3 Remove the banner step from `Start-Ledger.ps1` (end after Remote mode is `ready` with a line pointing at the dashboard QR dialog) and from `gateway/Start-Gateway.ps1` (drop the call, update the help to say devices sign in only through Remote mode). Verify both scripts parse (`powershell -NoProfile -Command "[scriptblock]::Create((Get-Content -Raw <file>)) | Out-Null"`) and `Start-Ledger.ps1 -Help` still prints.
- [x] 2.4 Add a test through the real middleware: with Remote mode off, a request carrying the previous session's token returns 401; after it is switched on again that old token still returns 401 and the new one returns 200. Verify with `cd api; pytest`.

## 3. Docs

- [x] 3.1 Update `wiki/Backend-Security.md` (per-session in-memory token, no file, no `LEDGER_TOKEN`), `wiki/Gateway.md` (drop the rotate-by-deleting-the-file paragraph and the `gateway_signin.py` banner descriptions), `wiki/Setup-And-Run.md` (the banner and token-print note), `wiki/Repository-Layout.md` and `wiki/Backend-Data-Layer.md` (`.ledger/` no longer holds a token), `wiki/Backend-API-Routes.md` and `wiki/Testing.md` (module and test names), and the `gateway_signin.py` row in `api/CLAUDE.md`. Verify `cd api; python check_docs.py` passes.

## 4. Verify

- [x] 4.1 Run `cd api; pytest` and `cd web; npm test; npm run build` and confirm all pass; the frontend is untouched, so a failure there is a regression to investigate.
- [x] 4.2 Run `openspec validate rotate-remote-token --strict` and confirm it passes.
- [ ] 4.3 Manually, with Docker available: start with `.\Start-Ledger.ps1`, turn Remote on from the dashboard, scan the QR on a phone and confirm it signs in; turn Remote off and on and confirm the phone shows "This device isn't signed in" until it scans the new QR; confirm `api/.ledger/token` is not created.
