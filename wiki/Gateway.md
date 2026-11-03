# Gateway

This page explains the gateway, the Nginx container that lets another device on your network (a phone, tablet or another computer) reach the dashboard. It covers how it starts, how devices sign in, and how the container is built.

> Requirements live in `openspec/specs/network-access/spec.md`. This page describes how the code meets them, not what it must do.

## What the gateway is

- It is a containerized Nginx, started as its own third piece alongside the backend and frontend processes. See [Setup and run](Setup-And-Run.md) for those two.
- The backend and frontend never bind beyond loopback (the machine's own address, `127.0.0.1`), no matter what.
- The gateway is the only thing that ever grants LAN access.
- The term is also in the [Glossary](Glossary.md#gateway).

### Requirements

- It requires Docker Desktop (Windows or Mac).
- It relies on `host.docker.internal` reaching a loopback-only bind, which is a Docker Desktop behavior.
- See `openspec/changes/archive/2026-09-23-add-nginx-lan-gateway/design.md`.
- The backend and frontend must already be running.

## Starting and stopping it

### Normally: turn on Remote mode

- Normally you do not start the gateway yourself.
- Turn **Remote mode** on from the Ledger's Sessions page or the desktop widget. See the [Glossary](Glossary.md#remote-mode).
- The backend then starts Docker Desktop if needed, the frontend if it is not up, and the gateway.
- It then shows the sign-in QR code.
- In the Ledger the QR is a modal; on the widget it is a tooltip on the Ledger button.
- Both show `https://<address>:<port>` and never the token.
- Turning Remote mode off, or the 8 hours running out, runs `docker compose down`.
- It stops the frontend only if Remote mode started it.
- Docker Desktop is left running.
- The lifecycle is `api/app/infra/remote_gateway.py`, a state machine.
- It sits over `api/app/infra/remote_system.py`, which makes the real Docker, npm and port calls.
- See [Live sessions and prompts](Backend-Live-Sessions-And-Prompts.md).

### By hand

```powershell
cd gateway
.\Start-Gateway.ps1
```

- This builds and starts the gateway container (Nginx) and nothing else.
- It publishes on `GATEWAY_PORT`, default `8503`.
- With `Start-Ledger.ps1`, which saves its own choice, the port is the configured or saved port, else the next free one in 8501-8599.
- It signs no device in.
- Without Remote mode, every request from another device is refused.
- `.\Stop-Gateway.ps1` stops it.
- It does not touch the backend or frontend processes.
- Windows prompts to allow Docker or the gateway through the firewall the first time.
- Allow it on Private networks.

### Script details

- `Start-Gateway.ps1` loads the root `.env` (see [Setup and run](Setup-And-Run.md)).
- It then runs `docker compose up -d --build`.
- `Stop-Gateway.ps1` runs `docker compose down` and touches nothing else.

## Signing in from another device

### The QR code and the token

- Devices sign in with the QR code Remote mode shows.
- The QR encodes `https://<address>:8503/?token=<token>`.
- The token is the [access token](Glossary.md#access-token).
- It is made when Remote mode turns on and discarded when it turns off.
- Each Remote session therefore has its own token.
- A device signed in with an earlier token is refused until it scans the new code.
- Opening the link on another device signs it in.
- The token is stored in that browser's `localStorage` and stripped from the address bar.
- Every later request from that device carries `Authorization: Bearer <token>`.

### How the sign-in link is built

- `api/app/infra/gateway_signin.py` builds the sign-in link the QR encodes (`signin_url`).
- It also builds the address shown beside the QR (`display_url`).
- `remote_service.sign_in_code` calls it.
- The addresses come from `banner.discover_ipv4()`, so address-discovery logic lives in exactly one place.

### The certificate warning

- The gateway serves **HTTPS only**, with a self-signed certificate.
- There is no plain-HTTP listener to fall back to.
- Each new device's browser shows a one-time certificate warning on first visit.
- This is expected, not a misconfiguration.
- Accept the warning once.
- Do this only on a network you trust.
- The certificate is self-signed, so the encryption protects against snooping.
- The browser cannot vouch for who it is talking to.

## Who is allowed to do what

- A local request is one from this machine, through `localhost` or `127.0.0.1`.
- A local request needs no token at all.
- Every other request needs the token.
- `SecurityMiddleware` in `api/app/core/security.py` checks it. See [Security](Backend-Security.md).
- The gateway adds no auth of its own; it only relays.
- Both proxy locations forward `X-Real-IP`, `X-Forwarded-For` and `Host`.
- So the existing "relayed by a proxy = treat as remote" rule in `api/app/core/security.py` gates gateway traffic.
- It gates it exactly as it always gated the old `--lan` mode.

### Where a token is not enough

- Deleting a session or project needs a *local* request outright.
- Switching Remote mode needs a *local* request outright.
- Answering a live session's prompts from another device needs Remote mode on.
- See [Live sessions and prompts](Backend-Live-Sessions-And-Prompts.md).

## Port rules

### `GATEWAY_PORT` must not be a restricted Chromium port

- Chromium restricts some ports, for example `10080`.
- `10080` was this project's own original default and broke exactly this way.
- Chrome and every Chromium-based mobile browser silently refuse to attempt a connection to those ports (`ERR_UNSAFE_PORT`).
- There is nothing to see server-side.
- `curl`, `Test-NetConnection` and the like still succeed; only actual browsers fail.
- That makes it easy to misdiagnose as a firewall or Docker networking problem.
- Pick an ordinary high port instead: `8503`, or anything else not on Chromium's list.

### Backend options

- The backend's `--host`, `--port` and `--frontend-port` still override its own bind address, its port, and the port it prints a frontend link for.
- The env vars `LEDGER_HOST`, `LEDGER_PORT` and `LEDGER_FRONTEND_PORT` do the same.
- `--frontend-port` is cosmetic only now.
- CORS is gone entirely, since the frontend never calls the backend cross-origin any more.
- Passing `--lan` is a removed no-op.
- It exits with an error pointing at the gateway instead.

## Large file transfers

- `location /api/files` is more specific than `/api/`.
- It turns off the 1 MB body limit.
- It turns off request and response buffering.
- It allows hour-long transfers.
- A large file therefore streams straight to the backend.
- It does not fail with a 413 or spool to the container's disk.
- See [API routes](Backend-API-Routes.md) for the file-drop routes.

## How the container is built

### TLS

- The gateway terminates TLS and serves HTTPS only.
- The `Dockerfile` installs `openssl` at image build time.
- It generates a self-signed EC certificate and key at `/etc/nginx/certs/gateway.{crt,key}`.
- The certificate is valid for 10 years, with `CN=the-ledger-gateway` and SANs for `localhost` and `127.0.0.1`.
- It then removes `openssl` again.
- Docker's layer cache keeps the same certificate across rebuilds.
- A device that accepted it once is therefore not warned again until that layer is rebuilt.
- A LAN address has no stable hostname to get a real CA certificate for.
- That is why it is self-signed, with a one-time browser warning per device.

### Nginx config

- The template has a single `listen 443 ssl;` server, TLS 1.2 and 1.3.
- There is no plain-HTTP listener at all, so nothing can be downgraded.
- `docker-compose.yml` maps `${GATEWAY_PORT:-8503}` to container port 443.
- It passes `BACKEND_PORT` and `FRONTEND_PORT` through as container environment variables (defaults 8501 and 8502).
- `Dockerfile` builds `nginx:alpine`.
- It copies `nginx.conf.template` to `/etc/nginx/templates/default.conf.template`.
- The base image's entrypoint runs `envsubst` on it at container start.
- `envsubst` substitutes `${BACKEND_PORT}` and `${FRONTEND_PORT}` into `/etc/nginx/conf.d/default.conf`.
- `$host`, `$remote_addr` and `$proxy_add_x_forwarded_for` stay in the template as literals for Nginx itself.
- `envsubst` only touches names that are actually set environment variables.

### Proxy routes

- `location /api/` proxies to `http://host.docker.internal:${BACKEND_PORT}`.
- `location /` proxies to `http://host.docker.internal:${FRONTEND_PORT}`.
- `host.docker.internal` is Docker Desktop's mechanism for a container to reach a host process bound to loopback only.
- It works on Windows and Mac only.
- That is why the gateway needs Docker Desktop specifically.
- The hop behind the gateway (gateway to `host.docker.internal` to backend or frontend) stays plain HTTP.
- That hop is loopback-only on the host.
- The gateway-to-device hop is therefore the only one on the network at all.
