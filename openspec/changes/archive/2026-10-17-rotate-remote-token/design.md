## Context

See proposal.md for why. Today `deps.access_token` is set once per process from `provision_token()`
(env var, else `api/.ledger/token`). `SecurityMiddleware` reads it on every request through a
callable and already refuses every non-local request while it is `None`. `RemoteGateway`
(`api/app/infra/remote_gateway.py`) owns the Remote lifecycle and is built by `deps.make_remote`
with two callbacks, `on_ready` and `on_off`. `stop()` is the single path to off for the switch and
for the 8 hour expiry timer (`self._schedule(self._ttl, self.stop)`); `_fail` goes to `failed`
without calling `stop()`. `start()` is already a no-op while starting or ready. `remote_service.sign_in_code`
builds the QR from `deps.access_token`. A second consumer, `gateway_signin.py`, reads the token file
from a separate process to print a terminal banner.

## Goals / Non-Goals

**Goals:**
- The token's lifetime is exactly one Remote session, with no copy on disk.
- No window in which Remote mode is up but the token is missing, or down but the token is valid.

**Non-Goals:**
- Expiring a token on its own timer inside a session (the 8 hour Remote limit already bounds it).
- Per-device tokens, revocation of single devices, or a regenerate control.
- Changing the locality rules, CSRF header or the download-ticket exception.

## Decisions

**1. Tie the token to `RemoteGateway`'s transitions through callbacks, not to the service layer.**
Add an `on_start` callback beside `on_ready`/`on_off`; `deps.make_remote` wires `on_start` to mint
and `on_off` to also clear. Rationale: the expiry timer calls `stop()` directly and never passes
through `remote_service.set_enabled`, so a service-level hook would miss it. Alternative: clear in
`set_enabled` and also in the timer: two places to forget, rejected.

**2. Mint synchronously inside `start()`, under the lock, only on the off/failed to starting
transition.** `start()` returns before the gateway container exists, and the early `return` for
starting/ready already gives the "no re-mint while on" behavior for free. Calling `on_start` inside
the lock (the callbacks only assign an attribute or flip the prompt gate and never take the gateway
lock) makes the transition and the token change atomic. Alternative: mint in the worker thread once
ready: leaves a window where the gateway answers with no token, and a started-then-superseded run
could clobber a newer token, rejected.

**3. Revoke before teardown, on every route to off.** `stop()` calls `on_off` under the lock, right
after setting `off`, instead of after `_teardown()` (which can wait on `docker compose down`). A
concurrent `start()` then cannot be followed by a stale `on_off` wiping its fresh token, because both
run under the same lock in order. `_fail` also calls `on_off` (guarded by the generation check) so a
failed start leaves no valid token. `on_off` stays idempotent: it already only closes the prompt gate.

**4. The token is `secrets.token_urlsafe(32)` held in `deps.access_token`.** Keep the existing
attribute so `SecurityMiddleware(token=lambda: deps.access_token)` and every test that
monkeypatches `deps.access_token` keep working. A small `new_token()` in `core/security.py` replaces
`provision_token`; `LEDGER_DIR` and `TOKEN_ENV` are removed from there, since only the token code
and the banner used them.
Alternative: a `TokenStore` class with its own lock: more structure than one attribute that is only
written under `RemoteGateway`'s lock.

**5. Startup stops provisioning.** Delete the `provision_token()` calls in `cli.main` and `main.lifespan`
(and the comment explaining the `--reload` subprocess), leaving `deps.access_token = None` until Remote
mode turns on. The `--reload` subprocess needs no special handling any more.

**6. Remove the terminal banner entirely.** Delete the root `api/gateway_signin.py` script and
`main()`, `read_token`, `build_signin_banner` and their parser from `app/infra/gateway_signin.py`; keep
`signin_url` and `display_url`, which `remote_service` uses. `Start-Ledger.ps1 -Remote` ends after
Remote mode reaches `ready` with a line pointing at the dashboard's QR dialog.
`gateway/Start-Gateway.ps1` loses the banner step and its help text. Alternative: let the script call
the local QR endpoint: rejected in exploration, since the dialog is the single sign-in path.

## Risks / Trade-offs

- [`Start-Gateway.ps1` starts a gateway outside Remote mode, so no token exists and no device can
  sign in through it] → Accepted: Remote mode (dashboard or `Start-Ledger.ps1 -Remote`) is the
  supported way to expose the gateway. The script's help says so.
- [`docker compose down` fails on stop, leaving the container up] → The cleared token makes the
  middleware return 401 to everything relayed through it; the failure is already logged.
- [A phone signed in earlier sees "This device isn't signed in" after every Remote cycle] → Intended;
  the existing unauthorized state and the new QR are the recovery path.
- [Users who set `LEDGER_TOKEN` or script against `api/.ledger/token` lose that path] → Documented as
  breaking in the proposal; Migration below.

## Migration Plan

No data migration. An existing `api/.ledger/token` is left in place and ignored. Rollback is reverting the change: the old code regenerates the file on its next start.
