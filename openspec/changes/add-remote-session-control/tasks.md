## 1. Backend: pending-decision store

- [x] 1.1 Add `api/pending_decisions.py`: lock-guarded, in-memory, per-session `{tool_name, tool_input,
      created_at, asyncio.Event, answer}` plus a `last_watched: dict[session_id, float]` heartbeat map,
      following `live_snapshot.py`'s pattern. Verify with a unit test exercising register → answer →
      resolve, and register → timeout → pass-through, without touching any real session.
- [x] 1.2 Add `touch_watch(session_id)` / `is_watched(session_id)` helpers (heartbeat freshness window,
      e.g. 5s) and a configurable decision wait timeout (default 120s). Verify with a unit test that an
      unwatched session's `request_decision()` returns immediately with `decision=None`.

## 2. Backend: routes

- [x] 2.1 Add `POST /api/sessions/{id}/decisions` (relay hook → api; local request, no token needed
      under the existing local-bypass rule). Body `{tool_name, tool_input}`; implements the
      watched/unwatched gate from design.md and responds
      `{decision: "allow"|"deny"|null, reason: string|null}`. Verify with a `TestClient` test covering
      unwatched (immediate pass-through) and watched-then-answered paths.
- [x] 2.2 Add `GET /api/sessions/{id}/pending-decision`, gated like the existing session routes, that
      both returns the current pending decision (if any) and calls `touch_watch(id)` as a side effect.
      Verify the side effect with a test: watch, then confirm `is_watched()` is true briefly after.
- [x] 2.3 Add `POST /api/sessions/{id}/decisions/answer` (browser-facing; token + `X-Requested-With`
      required like every other non-GET route). Body `{decision: "allow"|"deny", reason?: string}`;
      resolves the pending `Event`; `409` if nothing is pending. Verify with a test for the happy path
      and the `409` race.
- [x] 2.4 Extend `GET /api/live`'s per-session payload with `pending_decision: {tool_name, tool_input} |
      null`, sourced from `pending_decisions`. Verify with a `test_api_data.py` case.
- [x] 2.5 Add `POST /api/sessions/{id}/open-repo` (token-gated): resolve `cwd` server-side from the live
      registry (never from the request), then `subprocess.run` the repo's own
      `hooks/scripts/Open-ClaudeRepoWindow.ps1` with a `claudecode://open?path=<encoded cwd>` argument.
      404 for an unknown/non-live session. Verify with a test that stubs `subprocess.run` and asserts
      the constructed command/URI, plus a 404 case.
- [x] 2.6 Add an `is_local` locality check (reusing `security.py`'s existing local-request test) to
      both `DELETE /api/sessions/{id}` and `DELETE /api/projects`, refusing either when the request
      isn't local, independent of whether a valid token was presented. Add `is_local: bool` to
      `GET /api/meta`'s response, computed the same way. Verify with `test_security.py`/`test_api_data.py`
      cases: a local delete with no token succeeds, a remote delete with a valid token is refused, and
      `/api/meta` reflects `is_local` correctly for a local vs. a simulated-remote request.

## 3. Relay hook script

- [ ] 3.1 Create `hooks/ledgerScripts/Relay-PreToolUse.ps1`: parse the `PreToolUse` stdin payload,
      read `$env:LEDGER_PORT` (default 8501), POST to `/api/sessions/<id>/decisions` with a
      client-side timeout a few seconds above the server's own wait, and translate the response into
      `hookSpecificOutput.permissionDecision` — `allow`, `deny` (+ `permissionDecisionReason`), or no
      output at all for `decision: null`. Any connection failure also produces no output. Verify by
      running it manually against a live local `api/` instance for both an answered and an unanswered
      decision, and against a stopped backend to confirm silent, immediate pass-through.

## 4. Install / uninstall

- [ ] 4.1 Add an `-IncludeSessionControl` switch to `Install-ClaudeHooks.ps1` that copies
      `hooks/ledgerScripts/` to `%USERPROFILE%\.claude\hooks\ledgerScripts\` and merges the
      `PreToolUse` hook entry (matcher `Bash|Edit|MultiEdit|Write|WebFetch`) into `settings.json`,
      independent of the toast-hook install. Verify by running it in isolation (no toast hooks
      selected) and inspecting the resulting `settings.json` and installed files.
- [ ] 4.2 Add the matching `-IncludeSessionControl` switch to `Uninstall-ClaudeHooks.ps1`, removing
      only the `PreToolUse` entry (matched by its script path) and the `ledgerScripts` folder, leaving
      any installed toast hooks untouched. Verify by installing both, uninstalling only the session
      control hook, and confirming the toast hooks and `Notification`/`Stop` entries remain.
- [ ] 4.3 Update `hooks/README.md` with a new, clearly optional section documenting the relay hook:
      what it does, its install/uninstall commands, and the matcher/timeout defaults.

## 5. Frontend: live control view

- [ ] 5.1 Add `pending_decision` to `web/src/api/types.ts`'s live-session shape and a query hook (e.g.
      `usePendingDecision(sessionId)` polling `GET /api/sessions/{id}/pending-decision` while mounted)
      and mutation hooks for answering a decision and triggering open-repo, in `web/src/api/queries.ts`.
      Verify with `npm test` covering the new hooks' request shapes.
- [ ] 5.2 In `SessionDialog.tsx`, when `from === "live"`, render a new control-only view instead of
      `Detail`: the pending decision (tool name + input) with Approve/Deny (Deny opens an optional
      one-line reason field) when present, an "Open repo window" button always, and a `409`/timeout
      state ("this session already moved on") handled gracefully. Verify by running the app against a
      live session and a hook-driven permission prompt end to end (see task 6.1), and confirm `from ===
      "all"` selections are visually unchanged.
- [ ] 5.3 Add a pending-decision badge to the Live list row itself (sourced from `GET /api/live`'s new
      field), so a decision is visible without opening the dialog. Verify visually against a live
      session with a pending decision.
- [ ] 5.4 Read `is_local` from `useMeta()` and hide both delete controls entirely when it's false:
      `SessionDialog`'s `DeleteControls` (All-list detail view) and `ProjectsList`'s delete-row flow.
      Verify with `npm test`/manual check: open the app through the gateway (or simulate a remote
      request) and confirm neither delete control renders, while a local open still shows both.

## 6. End-to-end verification

- [ ] 6.1 With the relay hook installed, start a live session, trigger a matched tool call (e.g.
      `Bash`) while the session's control view is open in a browser, and confirm: the decision appears
      in the UI within a couple of seconds, Approve lets the tool run, Deny (with a reason) blocks it
      and the session sees the reason.
- [ ] 6.2 Confirm the "never changes local behavior" guarantees: (a) with the hook installed but the
      control view closed, a matched tool call behaves exactly as before (prompts locally if it would
      have, silent if pre-allowed); (b) with the backend stopped, same result, with no noticeable
      delay.
- [ ] 6.3 Confirm "Open repo window" both focuses an already-open VS Code window and opens a new one
      when the repo isn't open yet, from a live session's control view.

## 7. Gateway: HTTPS

- [ ] 7.1 Generate a self-signed certificate/key for the gateway (e.g. at Docker image build time via
      `openssl` in the `Dockerfile`, so no manual step is needed) and point Nginx's `server` block at
      HTTPS (443 inside the container, published on `GATEWAY_PORT`) instead of HTTP; remove the plain-
      HTTP listener rather than adding HTTPS alongside it. Verify by rebuilding the gateway and
      confirming `http://` no longer connects while `https://` serves the app (with the expected
      self-signed-certificate warning).
- [ ] 7.2 Update `api/gateway_signin.py` to print `https://` links and encode the QR with the HTTPS
      address. Verify with `test_gateway_signin.py` asserting the scheme.
- [ ] 7.3 Confirm end-to-end: `Start-Gateway.ps1` prints an `https://` link, opening it on a phone
      shows a one-time certificate warning, accepting it signs the device in exactly as before, and
      every subsequent request still carries the token correctly.

## 8. Documentation

- [ ] 8.1 Update CLAUDE.md: `hooks/` section notes it now also holds the optional, dashboard-coupled
      `ledgerScripts/`; `api/` section documents its `subprocess` dependency on
      `hooks/scripts/Open-ClaudeRepoWindow.ps1` for the open-repo action and the new `is_local`
      delete-locality check; `gateway/` section documents the HTTPS-only listener and self-signed
      certificate; note the new routes and `is_local` in the existing endpoint table.
