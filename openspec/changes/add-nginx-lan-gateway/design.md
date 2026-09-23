## Context

See proposal.md - Why. Today `network-access`'s LAN story lives entirely inside `api/server.py`
(`--lan` binds `0.0.0.0`, discovers addresses, prints a token+QR banner) and the frontend's
`apiOrigin()` calls the backend cross-origin on its own port whenever it isn't `vite dev`. This
design keeps that token-based auth model (`security.py`) completely unchanged and replaces only the
*transport*: a containerized Nginx becomes the one thing that ever binds a LAN-facing address;
`python server.py` and `vite preview` go back to being purely local processes, reached by the
gateway container over `host.docker.internal` (the Docker Desktop for Windows/Mac mechanism for a
container to reach a host-run service — this design targets Docker Desktop specifically, see
Non-Goals).

## Goals / Non-Goals

**Goals:**
- One URL/port for every secondary device, routed by Nginx to the backend and frontend.
- Backend and frontend never bind beyond loopback again; the gateway container is the only
  LAN-facing surface, shrinking what Windows Firewall needs to allow.
- Reuse the existing bearer-token check unmodified — the gateway adds no auth of its own.
- Frontend always calls relative `/api/...`, whether reached directly (`vite preview`) or through
  the gateway.

**Non-Goals:**
- TLS/HTTPS termination at the gateway. The `network-access` spec's "unencrypted, trusted-network-
  only" caveat still applies; Nginx being the natural place to add TLS later is a nice property, not
  something this change does.
- Support for Docker Engine on Linux (or any non-Docker-Desktop runtime). `host.docker.internal`'s
  ability to reach a loopback-only bind is a Docker Desktop (Windows/Mac) behavior; native Linux
  Docker's `host-gateway` mechanism routes over a real bridge IP and does not reach `127.0.0.1`-only
  binds, so this design does not attempt to support that target.
- Containerizing the backend or frontend. Both stay host processes (the backend needs direct
  filesystem access to `~/.claude.json`/`~/.claude/projects/`).

## Decisions

**1. `host.docker.internal` is the intended bridge from container to host-bound loopback services.**
Docker Desktop's VM networking forwards host-destined traffic in a way that (per current
understanding) reaches ports bound only to `127.0.0.1`, unlike native Linux Docker. This is the
single load-bearing assumption of the whole design and is unverified from documentation alone — the
first task must be a throwaway spike (bind a test server to `127.0.0.1`, curl it from a bare `nginx`
container via `host.docker.internal`) before any real config is written. If it fails, the fallback is
binding the backend/frontend to a specific non-`0.0.0.0` interface Docker Desktop's gateway can
reach — not full network exposure, but a narrower one than today's `--lan`.

**2. The gateway gets its own top-level `gateway/` folder, alongside `api/`, `web/`, `hooks/`.**
CLAUDE.md documents the repo as exactly three self-contained top-level folders, one per service. The
gateway is a fourth service in that same sense (its own Dockerfile, Nginx config, compose file,
nothing shared with `api/`/`web/` beyond the ports it proxies to), so it earns the same treatment
rather than being bolted onto the root or into `api/`. CLAUDE.md's repo-layout paragraph gets updated
to say "four top-level folders" as part of this change.
*Alternative considered*: put Docker artifacts at the repo root (`docker-compose.yml`,
`nginx.conf`). Rejected — it breaks the "root holds only cross-cutting docs/tooling, nothing that
runs" rule for no benefit; the compose file only ever builds/runs the gateway container, so it's
exactly as self-contained inside `gateway/` as `api/`'s `requirements.txt` is inside `api/`.

**3. Nginx proxies to the already-running `vite preview`/`python server.py` processes; it does not
serve `web/dist` itself.** Keeps exactly one thing responsible for "is the built frontend being
served" (the documented `npm run preview` step), so there's no second, possibly-stale copy of
`dist` living inside the gateway image/volume.
*Alternative considered*: mount `web/dist` into the Nginx container and serve it as static files
directly, skipping `vite preview` for the gateway path. Rejected for this change — it would mean the
frontend is served two different ways depending on entry point (direct vs. gateway), doubling what
needs to be documented and kept in sync, to save one proxy hop that costs nothing meaningful on a
LAN. Worth revisiting later if `vite preview` itself becomes a pain point.

**4. Token provisioning on the backend becomes unconditional, no longer gated by `--lan`.** Since
`--lan` is going away, *something* still needs to guarantee `api/.ledger/token` exists and is stable
before a device can ever sign in through the gateway. Simplest: `provision_token()` always runs on
backend start, same as it does today for `LEDGER_TOKEN`-set installs. The backend stays otherwise
unaware that a gateway exists.

**5. LAN-address discovery and the sign-in banner/QR move to a small gateway-side helper, not the
backend.** The backend no longer knows it's reachable over the network, so it can't print a
gateway address for it. A small script alongside the gateway (invoked when the gateway container is
started, e.g. via `docker compose up` or a wrapping script) reads the already-provisioned token from
`api/.ledger/token`, reuses `banner.discover_ipv4()`'s address-discovery logic, and prints
`http://<address>:<gateway-port>/?token=<token>` plus the QR — same content as today's banner, same
source of truth for the token, just triggered from a different place. Exact shape (PowerShell
script vs. a new backend CLI subcommand that only prints, doesn't bind) is a tasks-level detail; the
design constraint is that address-discovery logic isn't duplicated, it's reused from `banner.py`.
*Alternative considered*: have the frontend container/page detect the gateway and display the link
in-app instead of a startup banner. Rejected — the app's shell needs no token to load (per
`network-access`'s page-shell requirement), so there's no reliable moment to show this before the
user already needs the token; a printed banner at gateway-start keeps the same UX as today.

**6. CORS is dropped, not shrunk.** Once the frontend only ever calls relative `/api/...` — via
`vite dev`'s proxy (already true), `vite preview`'s new proxy (this change), or the gateway's proxy
— no browser page is ever served from a different origin than the one it calls. That means the
backend never receives a legitimate cross-origin browser request, so `CORSMiddleware` has nothing
left to allow. Removing it (rather than keeping an empty allow-list) is strictly at least as
protective as today's allow-list approach, and removes `cors_origins()`/`configure_cors()` and the
`--frontend-port`-driven allow-list entirely. The `network-access` spec's cross-site-read
requirement is still satisfied — by there being no allowed origin at all, rather than by an
allow-list scoped to the frontend's own origin.

## Risks / Trade-offs

- [Risk] `host.docker.internal` might not reach a `127.0.0.1`-only bind on some Docker Desktop
  version → Mitigation: Decision 1's spike runs before any other implementation work; if it fails,
  fall back to a narrower host bind rather than reintroducing `0.0.0.0`.
- [Risk] Docker Desktop becomes a hard runtime dependency for any secondary-device access, where
  today it's just two Python/Node processes → Mitigation: none needed technically, but CLAUDE.md
  must say so plainly so it isn't a surprise.
- [Risk] Removing `--lan` breaks anyone's existing muscle memory/scripts that pass it →
  Mitigation: keep `--lan` recognized by the CLI parser but have it fail fast with a message
  pointing at the gateway, instead of becoming a silent "unrecognized argument."
- [Risk] Gateway-side address-discovery helper duplicates backend logic if written carelessly →
  Mitigation: Decision 5 requires it to reuse `banner.discover_ipv4()`, not reimplement discovery.

## Migration Plan

This is a local dev tool, not a deployed service — there are no users to migrate and no data
involved, so this is a normal sequenced implementation rather than a staged rollout:

1. Spike `host.docker.internal` reachability to a loopback-only bind (Decision 1) before writing
   real config.
2. Add `gateway/` (Dockerfile, Nginx config, compose file) once the spike passes.
3. Update the frontend (`vite.config.ts` preview proxy, `apiOrigin()` simplification, drop
   `VITE_API_PORT`) and its tests.
4. Update the backend (remove `--lan`, unconditional token provisioning, drop CORS, reject `--lan`
   with a pointer to the gateway) and its tests.
5. Build the gateway-side banner/QR helper (Decision 5).
6. Update CLAUDE.md's "Setup & Run" and repo-layout paragraphs.
7. Manually verify from an actual phone on the LAN.

Rollback, if the spike in step 1 fails or the approach doesn't pan out, is a plain revert — nothing
in this change is destructive or hard to undo.
