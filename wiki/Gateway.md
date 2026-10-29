# Gateway

> Requirements live in `openspec/specs/network-access/spec.md`. This page describes how the code meets them, not what it must do.

**From another device on your network** (phone, tablet, another computer): the backend and frontend
(see [Setup and run](Setup-And-Run.md)) never bind beyond loopback, no matter what — the only thing
that ever grants LAN access is a containerized Nginx gateway, started as its own third piece
alongside those two processes.
Requires Docker Desktop (Windows/Mac; this relies on `host.docker.internal` reaching a
loopback-only bind, a Docker Desktop behavior — see
`openspec/changes/archive/2026-09-23-add-nginx-lan-gateway/design.md`). With the backend and frontend already
running. **Normally you don't start it yourself:** turn **Remote mode** on from the Ledger's Sessions
page or the desktop widget and the backend starts Docker Desktop if needed, the frontend if it isn't
up, and the gateway, then shows the sign-in QR (a modal in the Ledger, a tooltip on the widget's Ledger
button; both show `https://<address>:<port>` and never the token). Turning it off, or the 8 hours
running out, runs `docker compose down` and stops the frontend only if Remote mode started it; Docker
Desktop is left running. The lifecycle is `api/app/infra/remote_gateway.py` (state machine) over
`api/app/infra/remote_system.py` (the real Docker/npm/port calls); see
[Live sessions and prompts](Backend-Live-Sessions-And-Prompts.md). To run just the container by hand:

```powershell
cd gateway
.\Start-Gateway.ps1
```

This builds/starts the gateway container (Nginx, published on `GATEWAY_PORT`, default `8503`; with
`Start-Ledger.ps1`, which saves its own choice, it's the configured or saved port, else the next free one
in 8501-8599) and nothing else: it signs no device in, and without Remote mode every request from another device is
refused. Devices sign in with the QR Remote mode shows, which encodes
`https://<address>:8503/?token=<token>`. The token is made when Remote mode turns on and discarded
when it turns off, so each Remote session has its own and a device signed in with an earlier one is
refused until it scans the new code. The gateway serves **HTTPS
only**, with a self-signed certificate (there's no plain-HTTP listener to fall back to), so each
new device's browser shows a one-time certificate warning on first visit — expected, not a
misconfiguration; accept it once. Opening that link on another
device signs it in (the token is stored in that browser's `localStorage` and stripped from the
address bar) and every subsequent request from it carries `Authorization: Bearer <token>`. A local
request (from this machine, via `localhost`/`127.0.0.1`) needs no token at all; every other request
needs it, checked by `api/app/core/security.py`'s `SecurityMiddleware` (see [Security](Backend-Security.md)) exactly as
before — the gateway adds no auth of its own, it only relays. A token is not enough for everything,
though: deleting a session/project and switching Remote mode need a *local* request outright, and
answering a live session's prompts from another device needs Remote mode on (see [Live sessions and prompts](Backend-Live-Sessions-And-Prompts.md)). Only do this on a network you trust — the certificate is self-signed, so the encryption
protects against snooping but the browser can't vouch for who it's talking to. Windows will prompt to allow Docker/the gateway through the firewall the first time — allow it on
Private networks. Stop it with `.\Stop-Gateway.ps1`; it doesn't touch the backend/frontend
processes.

**`GATEWAY_PORT` must not be one of Chromium's restricted ports** (e.g. `10080`, which was this
project's own original default and broke exactly this way) — Chrome, and every Chromium-based
mobile browser, silently refuses to even attempt a connection to those ports (`ERR_UNSAFE_PORT`),
with nothing to see server-side: `curl`/`Test-NetConnection` and the like still succeed, only actual
browsers fail, which makes this easy to misdiagnose as a firewall or Docker networking problem. Pick
an ordinary high port instead (`8503`, or anything else not on Chromium's list).

The backend's `--host`/`--port`/`--frontend-port` (or `LEDGER_HOST`/`LEDGER_PORT`/
`LEDGER_FRONTEND_PORT` env vars) still override its own bind address/port and the port it prints a
frontend link for — `--frontend-port` is cosmetic only now (CORS is gone entirely, since the
frontend never calls the backend cross-origin any more). Passing `--lan` is a removed no-op: it
exits with an error pointing at the gateway instead.

`location /api/files` (more specific than `/api/`) turns off the 1 MB body limit and request/response
buffering and allows hour-long transfers, so a large file streams straight to the backend instead of
failing with a 413 or spooling to the container's disk. See [API routes](Backend-API-Routes.md) for the
file-drop routes.

The only thing that ever grants LAN access (see [Setup and run](Setup-And-Run.md)); the backend and
frontend stay loopback-only always. It **terminates TLS and serves HTTPS only**: the `Dockerfile`
installs `openssl` at image build time to generate a self-signed EC certificate/key
(`/etc/nginx/certs/gateway.{crt,key}`, 10-year validity, `CN=the-ledger-gateway`, SANs for
`localhost`/`127.0.0.1`), then removes it again; Docker's layer cache keeps the same certificate
across rebuilds, so a device that accepted it once isn't warned again until that layer is rebuilt.
The template has a single `listen 443 ssl;` server (TLS 1.2/1.3) — no plain-HTTP listener at all, so
nothing can be downgraded — and `docker-compose.yml` maps `${GATEWAY_PORT:-8503}` to container port
443. The hop behind it (gateway → `host.docker.internal` → backend/frontend) stays plain HTTP: it's
loopback-only on the host, so the gateway-to-device hop is the only one that's on the network at
all. A LAN address has no stable hostname to get a real CA certificate for, hence self-signed and
the one-time browser warning per device. `Dockerfile` builds `nginx:alpine` with `nginx.conf.template`
copied to `/etc/nginx/templates/default.conf.template` — the base image's entrypoint runs `envsubst`
on it at container start, substituting `${BACKEND_PORT}`/`${FRONTEND_PORT}` (left in the template as
literal `$host`/`$remote_addr`/`$proxy_add_x_forwarded_for` for Nginx itself, since `envsubst` only
touches names that are actually set environment variables) into
`/etc/nginx/conf.d/default.conf`. `location /api/` proxies to
`http://host.docker.internal:${BACKEND_PORT}`; `location /` proxies to
`http://host.docker.internal:${FRONTEND_PORT}` — `host.docker.internal` is Docker Desktop's
mechanism for a container to reach a host process bound to loopback only (Windows/Mac only; this is
why the gateway needs Docker Desktop specifically). Both locations forward
`X-Real-IP`/`X-Forwarded-For`/`Host`, so `api/app/core/security.py`'s existing "relayed by a proxy = treat as
remote" rule gates gateway traffic exactly like it always gated the old `--lan` mode — the gateway
adds no auth of its own. `docker-compose.yml` publishes the container on `${GATEWAY_PORT:-8503}`
and passes `BACKEND_PORT`/`FRONTEND_PORT` through as container environment variables (defaults
8501/8502). `Start-Gateway.ps1` loads the root `.env` (see [Setup and run](Setup-And-Run.md)), runs
`docker compose up -d --build`; `Stop-Gateway.ps1` runs `docker compose down` and touches nothing
else. The sign-in link the QR encodes and the address shown beside it are built by
`api/app/infra/gateway_signin.py` (`signin_url`/`display_url`), called from `remote_service.sign_in_code`,
which takes the addresses from `banner.discover_ipv4()` so address-discovery logic lives in exactly one place.
