## Why

Reaching the app from a phone or another device today means opening two separately-ported
addresses (`--lan`-bound frontend and backend processes), and the frontend's API client carries
permanent cross-origin logic (`VITE_API_PORT`, a different port per environment) just to make that
work. Collapsing LAN access behind a single containerized Nginx gateway gives one URL/port for
every secondary device, lets the backend and frontend stop binding beyond loopback at all (a
smaller network footprint than today's `--lan` mode), and removes the need for the frontend to ever
call a different origin than its own.

## What Changes

- Add a containerized Nginx reverse proxy as the only process that ever binds a LAN-facing address.
  It listens on one configurable port and routes `/api/*` to the backend and everything else to the
  frontend, both reached on the host via `host.docker.internal`.
- **BREAKING**: Remove the backend's `--lan` option and its LAN-bind mode entirely. The backend and
  frontend SHALL always bind to loopback only from now on; today's `--lan`-triggered LAN-address
  discovery, QR code, and banner output on the backend are removed. Sign-in messaging (the
  printed address + token + QR) moves to wherever the gateway is started, pointing at the gateway's
  single address instead of the frontend's own port.
- The gateway is the new trust boundary but adds no new auth of its own: it forwards requests
  transparently (standard `X-Forwarded-For`/`X-Real-IP`), so the backend's existing
  "a request relayed by a proxy is treated as remote and needs the token" rule (`security.py`)
  gates all gateway traffic unchanged. No backend auth logic changes.
- Simplify the frontend's API client to always call relative `/api/...` paths, dropping
  `VITE_API_PORT` and `apiOrigin()`'s different-port branch. `vite preview` gets its own local
  `/api` proxy (mirroring `vite dev`'s existing one) so direct local access (bypassing the gateway)
  keeps working unchanged.
- Shrink the backend's CORS allow-list now that LAN devices never call it cross-origin — only the
  local dev/preview origins remain.
- Add the Nginx/Docker artifacts (image config, compose file) needed to run the gateway.

## Capabilities

### New Capabilities

(none — the gateway changes *how* LAN access is granted, not what access is granted; that
behavior is already owned by `network-access`.)

### Modified Capabilities

- `network-access`: the mechanism for granting other devices access changes from each process
  binding to `0.0.0.0` under `--lan` to a single containerized Nginx gateway sitting in front of
  loopback-only processes. Requirements affected: local-only-by-default (the backend/frontend no
  longer have a network-bind mode at all — the gateway is the only thing that does), the token
  requirement for non-local requests (unchanged in mechanism, now the universal path for gateway
  traffic), cross-site/rebinding protections (still enforced, now always via the "relayed by a
  proxy" branch rather than as an edge case), and startup messaging (the printed sign-in
  link/QR/token now describes the gateway's address, not the frontend's own port).

## Impact

- `api/server.py`: remove `--lan`, LAN-address discovery, and the LAN entries in `cors_origins()`.
- `api/banner.py`: LAN URL/QR/token messaging is removed from (or relocated out of) the backend's
  own startup output.
- `api/security.py`: no behavior change, but its docstring/comments currently describe
  proxy-relayed requests as the exception — they become the normal LAN path.
- `web/vite.config.ts`: add a `preview.proxy` entry for `/api` alongside the existing dev one.
- `web/src/api/client.ts`: `apiOrigin()` simplifies to always return `""` (relative).
- `CLAUDE.md`: "Setup & Run" needs a rewrite for the gateway-based LAN flow in place of `--lan`.
- New Nginx/Docker config and a compose file. **Open question for design.md**: CLAUDE.md currently
  documents the repo as exactly three self-contained top-level folders (`api/`, `web/`, `hooks/`),
  one per service, with the root holding only cross-cutting docs/tooling. A fourth service (the
  gateway) needs a home that either fits or deliberately revises that convention — to be resolved
  in design.md, not decided here.
- Tests: `api/tests/test_cli.py`, `test_server.py`, `test_banner.py` (backend behavior changes);
  frontend tests referencing `apiOrigin`/`VITE_API_PORT`.
