## 1. Spike: verify the load-bearing networking assumption

- [x] 1.1 Bind a throwaway Python `http.server` (or the real backend) to `127.0.0.1:8501` only,
      run a bare `nginx:alpine` container with `curl` and confirm
      `curl http://host.docker.internal:8501` from inside it succeeds. Verify: the curl returns the
      test server's response, not a connection error.
- [x] 1.2 If 1.1 fails, stop and report back before continuing — design.md's fallback (a narrower
      host bind reachable by Docker Desktop's gateway) needs to be chosen with the user, not
      assumed.

## 2. Gateway service

- [x] 2.1 Create `gateway/` as a new top-level, self-contained folder (Dockerfile, Nginx config,
      compose file), matching how `api/` and `web/` are organized. Verify: `docker compose config`
      (or equivalent) parses without error from inside `gateway/`.
- [x] 2.2 Write the Nginx config: `location /api/` proxies to `http://host.docker.internal:8501`
      with `X-Real-IP`/`X-Forwarded-For`/`Host` headers set; `location /` proxies to
      `http://host.docker.internal:4173`. Verify: with the backend and frontend running locally and
      the gateway container up, `curl http://localhost:<gateway-port>/api/meta` returns the same
      JSON as `curl http://localhost:8501/api/meta`, and `curl http://localhost:<gateway-port>/`
      returns the frontend's HTML shell.
- [x] 2.3 Make the gateway's listen port configurable (compose port mapping or an env var) with a
      documented default that doesn't collide with 4173/8501. Verify: changing the mapping changes
      which port answers, per a manual check.
- [x] 2.4 Confirm a request proxied through the gateway is refused without a token, and succeeds
      with the correct `Authorization: Bearer <token>` header, exercising the existing
      `SecurityMiddleware` unchanged. Verify: two `curl` calls through the gateway (with and
      without the header) return 401 then 200 for a data endpoint like `/api/meta`.

## 3. Frontend: always call relative `/api` paths

- [x] 3.1 Add a `preview.proxy` entry for `/api` to `web/vite.config.ts`, mirroring the existing
      `server.proxy` entry. Verify: `npm run build && npm run preview`, then a browser at
      `localhost:4173` successfully loads data (the Sessions page shows the Live/All lists).
- [x] 3.2 Simplify `apiOrigin()` in `web/src/api/client.ts` to always return `""`; remove the
      `VITE_API_PORT`/`DEFAULT_API_PORT` branch. Update `web/src/api/client.test.ts` accordingly.
      Verify: `npm test` passes.
- [x] 3.3 Remove `VITE_API_PORT` from any remaining references (env examples, comments in
      `client.ts`'s docstring). Verify: `grep -r VITE_API_PORT web/` returns nothing.
- [x] 3.4 Run the full frontend test suite and type check. Verify: `npm test` and `npm run build`
      both succeed.

## 4. Backend: drop `--lan`, unconditional token, no CORS

- [x] 4.1 Remove the `--lan` option's bind-mode behavior from `parse_settings`/`main` in
      `api/server.py`; keep `--lan` recognized by the argument parser but have it exit with an error
      pointing at the gateway instead of silently doing nothing. Verify: `python server.py --lan`
      prints that message and exits non-zero; `api/tests/test_cli.py` covers it.
- [x] 4.2 Make `provision_token()` run unconditionally on backend start (not gated by
      `settings.exposed`). Verify: starting the backend with no flags and no `LEDGER_TOKEN` still
      creates `api/.ledger/token`; update `api/tests/test_cli.py`.
- [x] 4.3 Remove `cors_origins()`/`configure_cors()` and the `CORSMiddleware` registration from
      `api/server.py` (design.md Decision 6). Verify: `api/tests/test_server.py`'s CORS-allow-list
      tests are removed/updated to assert no CORS middleware is present; full `pytest` suite passes.
- [x] 4.4 Remove LAN-address discovery and the QR/token banner content from `api/banner.py`'s
      backend-startup path (keep `discover_ipv4()` itself — task 5 reuses it) and update
      `api/tests/test_banner.py` for the backend's now-simpler startup message (local frontend
      address only, no network section). Verify: `pytest api/tests/test_banner.py` passes.

## 5. Gateway-side sign-in banner

- [ ] 5.1 Add a small helper (script or backend CLI subcommand — pick whichever keeps
      `banner.discover_ipv4()` as the single source of address-discovery logic per design.md
      Decision 5) that reads `api/.ledger/token` and prints
      `http://<address>:<gateway-port>/?token=<token>` plus a QR code for each discovered LAN
      address, invoked when the gateway starts. Verify: running it with the token file present
      prints a correct, working sign-in link (manually opening it signs a browser in).
- [ ] 5.2 Wire the helper into the gateway's startup (e.g. a `docker compose up` wrapper or a
      documented manual step). Verify: starting the gateway per the documented command shows the
      banner.

## 6. Documentation

- [ ] 6.1 Rewrite CLAUDE.md's "Setup & Run" `--lan` section to describe starting the gateway
      instead, including the new `gateway/` folder and its port. Verify: a fresh read-through
      matches the actual commands from tasks 2-5.
- [ ] 6.2 Update CLAUDE.md's repo-layout paragraph from "exactly three top-level folders" to four,
      describing `gateway/`'s contents alongside `api/`, `web/`, `hooks/`. Verify: matches what
      task 2.1 actually created.

## 7. End-to-end verification

- [ ] 7.1 With the backend and frontend running locally (no `--lan`) and the gateway container up,
      open the printed gateway link on an actual phone on the same LAN. Verify: the dashboard loads
      and shows live data.
- [ ] 7.2 Confirm direct local access still works unchanged: `localhost:4173` in a desktop browser
      loads and functions with no token needed. Verify: manual check, Sessions/Overview/Projects
      pages all load data.
