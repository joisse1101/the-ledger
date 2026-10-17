# Backend: security

> Requirements live in `openspec/specs/network-access/spec.md`. This page describes how the code meets them, not what it must do.

- `api/app/core/security.py` — one ASGI middleware gating every request (its requirements are the `network-access` spec).
  A request is **local** only when `request.client.host` is loopback (`127.0.0.1`/`::1`/
  `::ffff:127.0.0.1`) *and* carries none of `Forwarded`/`X-Forwarded-For`/`X-Real-IP` (so a tunnel or
  reverse proxy on the same machine is treated as remote, not silently trusted); local requests must
  still present `Host: localhost`/`127.0.0.1`/`[::1]` (any port) or get a 403 — this stops a public DNS
  name that resolves to 127.0.0.1 from reaching the app unauthenticated. Every non-local request needs
  the access token as `Authorization: Bearer <token>` (`hmac.compare_digest` comparison) or gets a 401
  with a message pointing back at the sign-in code — there is no `?token=` query handling or
  cookie on the API side at all; turning a sign-in link's `?token=` into that header is entirely the
  frontend's job (see [Frontend API layer](Frontend-Api-Layer.md)). Every non-GET request additionally needs an
  `X-Requested-With: ledger` header, which a page on another origin can't add without a CORS
  preflight — with no `CORSMiddleware` at all now, that preflight always fails, so that header is
  what stops a blind cross-site `POST`/`DELETE` even from a page that could otherwise read the API.
  The token belongs to one Remote mode session and lives only in memory (`deps.access_token`):
  `RemoteGateway` calls `deps.issue_token` (`security.new_token()`, `secrets.token_urlsafe(32)`) as it
  leaves off for starting, and `deps.end_remote_session` on every way back to off — the switch, the
  8 hour expiry and a failed start — before the Docker teardown. A second "turn on" while starting
  or ready keeps the same token. While it is `None` (Remote mode off, or the backend just started)
  every non-local request gets a 401, even if the gateway container were left running.
  The middleware's locality test is also exported as `is_local(request)`, which is what makes some
  things stricter than "has the token": both `DELETE` routes, `POST /api/remote-mode` and
  `POST /api/sessions/{id}/decisions` call it and refuse a non-local request with 403 regardless of
  any token (so a remote device can read, and — with Remote mode on — answer prompts, but never
  delete or flip Remote mode), and `GET /api/meta` reports it back as `is_local` so the frontend can
  hide those controls up front. The one request a non-local device may make without the token is a **file-drop download link**:
`GET /api/files/download/<ticket>`. `security.py` only matches that path shape (`_DOWNLOAD_LINK`, GET
only); the route redeems the ticket (single-use, 60 seconds, one file) and still refuses while Remote
mode is off, so the ticket, not the middleware, is the credential. A browser download can't carry the
bearer header, which is why this exists; see [API routes](Backend-API-Routes.md). The route-level check is the actual security boundary; hiding the
  buttons is only UX.
