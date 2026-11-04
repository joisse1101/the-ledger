# Backend: security

This page explains how the backend decides who may call it: what counts as a local request, how the access token works, and which routes refuse a remote device. The access token is defined in the [Glossary](../Glossary.md#access-token).

> Requirements live in `openspec/specs/network-access/spec.md`. This page describes how the code meets them, not what it must do.

## The middleware

`api/app/core/security.py` is one ASGI middleware that gates every request. Its requirements are the `network-access` spec.

## What counts as local

### The test

A request is **local** only when both of these hold:

- `request.client.host` is loopback: `127.0.0.1`, `::1` or `::ffff:127.0.0.1`.
- It carries none of `Forwarded`, `X-Forwarded-For` or `X-Real-IP`.

So a tunnel or reverse proxy on the same machine is treated as remote, not silently trusted.

### The Host header

A local request must still present `Host: localhost`, `127.0.0.1` or `[::1]`, with any port. Otherwise it gets a 403. This stops a public DNS name that resolves to 127.0.0.1 from reaching the app unauthenticated.

### `is_local(request)`

The middleware's locality test is also exported as `is_local(request)`. It is what makes some things stricter than "has the token".

These routes call it and refuse a non-local request with 403, regardless of any token:

- both `DELETE` routes
- `POST /api/remote-mode`
- `POST /api/sessions/{id}/decisions`
- both `/api/settings` routes (read and save)

So a remote device can read. With Remote mode on, it can also answer prompts. It can never delete, flip Remote mode or see settings.

`GET /api/meta` reports the result back as `is_local`, so the frontend can hide those controls up front. The route-level check is the actual security boundary. Hiding the buttons is only UX.

## What a non-local request needs

### The access token

Every non-local request needs the access token as `Authorization: Bearer <token>`. The comparison uses `hmac.compare_digest`. Without it the request gets a 401, with a message pointing back at the sign-in code.

There is no `?token=` query handling or cookie on the API side at all. Turning a sign-in link's `?token=` into that header is entirely the frontend's job. See [Frontend API layer](../Frontend/Api-Layer.md).

### The `X-Requested-With` header

Every non-GET request additionally needs an `X-Requested-With: ledger` header. A page on another origin cannot add that header without a CORS preflight. There is no `CORSMiddleware` at all now, so that preflight always fails.

So that header is what stops a blind cross-site `POST` or `DELETE`, even from a page that could otherwise read the API.

## The token's life

The token belongs to one Remote mode session. It lives only in memory (`deps.access_token`).

`RemoteGateway` calls `deps.issue_token` as it leaves off for starting. `deps.issue_token` uses `security.new_token()`, which is `secrets.token_urlsafe(32)`.

`RemoteGateway` calls `deps.end_remote_session` on every way back to off, before the Docker teardown. Those ways are the switch, the 8 hour expiry and a failed start.

A second "turn on" while starting or ready keeps the same token.

While the token is `None` (Remote mode off, or the backend just started), every non-local request gets a 401. That holds even if the gateway container were left running.

## The one request that needs no token

A non-local device may make one request without the token: a **file-drop download link**, `GET /api/files/download/<ticket>`. `security.py` only matches that path shape (`_DOWNLOAD_LINK`, GET only).

The route redeems the ticket, which is single-use, 60 seconds and one file. The route still refuses while Remote mode is off. So the ticket, not the middleware, is the credential.

A browser download cannot carry the bearer header, which is why this exists. See [API routes](API-Routes.md).
