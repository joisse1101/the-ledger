# Backend: live sessions and prompts

> Requirements live in `openspec/specs/remote-session-control/spec.md`. This page describes how the code meets them, not what it must do.

- `api/app/domain/live_snapshot.py` — `LiveSnapshot`, a lock-guarded, TTL-coalesced (`LIVE_TTL_SECONDS = 1.0`)
  wrapper around `claude_sessions.load_sessions()` + `claude_context.live_context()` per session, so
  N browsers/phones polling `/api/live` every ~2s cost about one recompute per second rather than N —
  those two modules' own caches assume a single caller, so every read of them from the API goes
  through this one lock. One session's `live_context()` raising leaves the others populated
  (`context: null` for that one). `is_live_now()` bypasses the TTL for delete decisions (see the
  `DELETE /api/sessions/{id}` route in [API routes](Backend-API-Routes.md)); `cwd_for()` is used server-side only, never sent to a
  client. `latest_activity()` (through the same lock) feeds the pending-prompt sweep below.
- `api/app/domain/pending_decisions.py` — `PendingDecisions`, the in-memory, lock-guarded store (same spirit as
  `LiveSnapshot`; nothing touches disk) behind answering a live session's blocking prompts from the
  dashboard, plus the **Remote mode** switch. The prompts come from the optional relay hook (see [Hooks](Hooks.md)): a `PermissionRequest` hook fires only when Claude Code is about to show a dialog
  (a tool-permission prompt or an `AskUserQuestion`), runs *alongside* the terminal dialog rather than
  in front of it, and POSTs the prompt to `/api/sessions/{id}/decisions`, which `register()`s it (an
  API-generated id, since Claude Code supplies none) and awaits it in `request_decision()`. Whichever
  surface answers first wins: a dashboard answer resolves the waiting request (`answer()`), which the
  hook hands back to Claude Code as the decision; a terminal answer is never heard directly, so
  `sweep()` clears the prompt when the session's transcript shows a new **`user`** line (the tool
  result) stamped after it was registered — only `user` lines count, since `assistant`/bookkeeping
  lines can appear while a dialog is still open — and releases the hook with "no answer" so it exits.
  A 30-minute maximum age is the backstop. `sweep()` isn't on a timer: `/api/live`, the
  pending-decision route and the answer route each run it first (`deps.sweep_prompts`), so an
  already-answered prompt gives a 409 rather than "succeeding". **Remote mode**'s access gate is only state here
  (`set_remote_mode`/`remote_mode`/`remote_mode_enabled`): in-memory, off after any backend restart,
  and only a local request can turn it on or off. It is purely an access gate on
  *other devices* — the hook always registers prompts and never hides the terminal dialog — so while
  it's off a non-local request sees no pending prompt and can't answer one, while the PC's own
  browser always can (`deps.can_see_prompts`).
- `api/app/infra/remote_gateway.py` — `RemoteGateway`, the lifecycle behind Remote mode. `POST /api/remote-mode`
  calls `start()`/`stop()`, which return at once; a state machine runs off, `starting` (with a `step`:
  `docker`, `frontend`, `gateway`), then `ready` or `failed` (with a `reason`, shown for 30 s), and
  `/api/meta.remote_mode` reports `{enabled, expires_at, state, step, reason}`. Only at `ready` does it
  open the access gate above and start the **8-hour** timer; turning off, the timer, a failure or a
  newer `start()` closes the gate and runs `docker compose down`, stopping the frontend only if it
  started it. It knows nothing about HTTP: everything touching the machine goes through a `System`
  object (`api/app/infra/remote_system.py`'s `RealSystem`: Docker Desktop, `docker compose`, the frontend
  process, port probes), which tests replace with a fake and never run for real.
- `GET /api/remote-mode/qr` returns the sign-in code as an SVG plus the token-free address and the
  expiry: local requests only, 409 unless `ready`.
- `POST /api/sessions/{id}/open-repo` shells out to `hooks/scripts/Open-ClaudeRepoWindow.ps1`
  (`OPEN_REPO_SCRIPT` in `api/app/routers/sessions.py`, `subprocess.run`, the script unmodified) with a
  `claudecode://open?path=<url-encoded cwd>` URI — the repo's own copy, not the one installed under
  `%USERPROFILE%\.claude\hooks\`, so `api/` now depends on that file in `hooks/` even though `hooks/`
  is otherwise standalone. It needs no install step, only that the API run from this checkout.
