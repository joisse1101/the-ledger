# Backend: live sessions and prompts

This page explains how the backend tracks running Claude Code sessions, holds their blocking prompts so the dashboard can answer them, and runs Remote mode. See the [Glossary](../Glossary.md) for live session, pending decision, auto-approve, Remote mode and relay hook.

> Requirements live in `openspec/specs/remote-session-control/spec.md`. This page describes how the code meets them, not what it must do.

## `LiveSnapshot`

### What it is

`api/app/domain/live_snapshot.py` defines `LiveSnapshot`. It is a lock-guarded, TTL-coalesced wrapper (`LIVE_TTL_SECONDS = 1.0`). It wraps `claude_sessions.load_sessions()` plus `tail.live_context()` per session.

### Why it exists

N browsers or phones polling `/api/live` every ~2s cost about one recompute per second, rather than N. Those two modules' own caches assume a single caller. So every read of them from the API goes through this one lock.

### Behavior

One session's `live_context()` raising leaves the others populated. That one session gets `context: null`.

`is_live_now()` bypasses the TTL for delete decisions. See the `DELETE /api/sessions/{id}` route in [API routes](API-Routes.md).

`cwd_for()` is used server-side only, never sent to a client. `latest_activity()` goes through the same lock and feeds the pending-prompt sweep below.

### The `compact` grade

Each item's `compact` grade comes from `tail.latest_activity()` and the pure `compact_grade.grade_compact`. `latest_activity()` returns the timestamp of the newest `user` line in the main transcript, so a tool result counts and sub-agent requests do not. A compaction writes new lines, so it restarts the clock too. The grade falls back to the session's `started_at` when there is no such line or the lookup fails. `started_at` is the conversation's first transcript timestamp, so reopening a session does not restart it.

The 45 and 55-minute limits are constants in `compact_grade`.

## `PendingDecisions`

### What it is

`api/app/domain/pending_decisions.py` defines `PendingDecisions`. It is the in-memory, lock-guarded store behind answering a live session's blocking prompts from the dashboard. It is in the same spirit as `LiveSnapshot`: nothing touches disk. It also holds the **Remote mode** switch.

### Where prompts come from

The prompts come from the optional relay hook. See [Hooks](../Services/Hooks.md). A `PermissionRequest` hook fires only when Claude Code is about to show a dialog. That is a tool-permission prompt or an `AskUserQuestion`. It runs alongside the terminal dialog, not in front of it.

It POSTs the prompt to `/api/sessions/{id}/decisions`. That route `register()`s the prompt, with an API-generated id, since Claude Code supplies none. It then awaits the prompt in `request_decision()`.

### Whichever surface answers first wins

A dashboard answer resolves the waiting request (`answer()`). The hook hands that back to Claude Code as the decision.

A terminal answer is never heard directly. So `sweep()` clears the prompt when the session's transcript shows a new `user` line, stamped after the prompt was registered. That `user` line is the tool result. Only `user` lines count. `assistant` and bookkeeping lines can appear while a dialog is still open.

`sweep()` then releases the hook with "no answer", so it exits. A 30-minute maximum age is the backstop.

### When `sweep()` runs

`sweep()` is not on a timer. `/api/live`, the pending-decision route and the answer route each run it first (`prompt_service.sweep`). So an already-answered prompt gives a 409 rather than "succeeding".

### Remote mode's access gate

The gate is only state here: `set_remote_mode`, `remote_mode` and `remote_mode_enabled`. It is in-memory and off after any backend restart. Only a local request can turn it on or off.

It is purely an access gate on other devices. The hook always registers prompts and never hides the terminal dialog. While it is off, a non-local request sees no pending prompt and cannot answer one. The PC's own browser always can (`prompt_service.can_see`).

## Auto-approve

### State

Auto-approve is per-session state in the same `PendingDecisions`. It is memory only and off after a backend restart. It lasts **8 hours**, like Remote mode. It is forgotten once the session leaves `/api/live`. The functions are `set_auto_approve`, `auto_approve_enabled`, `last_auto_approved` and `prune_auto_approve`.

### How it answers

While it is on, `request_decision()` answers `allow` the moment a prompt registers. `auto_approve_service.set_enabled` also approves what is already pending (`approve_pending`). It serves `POST /api/sessions/{id}/auto-approve`. That route is local requests only, and 404 unless the session is live.

### Races

The flag is set before the pending prompts are scanned. A prompt is registered before the flag is read. So a prompt racing the switch is caught by one side. `answer()` is False for a prompt already gone, so a prompt is answered once.

### What qualifies

`api/app/domain/auto_approve_policy.py`'s `is_auto_approvable` decides. It never approves `AskUserQuestion` or `ExitPlanMode`.

For `Bash` and `PowerShell`, it never approves an unreadable command. For `Bash` and `PowerShell`, it never approves a command matching `DANGEROUS_COMMAND_PATTERNS`. Examples are `sudo`, `rm -rf`, forced pushes, `curl | sh`, disk formatting, shutdown, and similar.

That list is a best-effort regex guard, **not a security boundary**. Obfuscation or a script file can slip past it.

### Logging and the UI wait

Each approval logs the session id and tool name, never `tool_input`. `relay_hook_seen` is set by the first `register()` since the backend started. It is reported in `/api/meta`. It is what the UIs wait for before offering the switch.

## `RemoteGateway`

### What it is

`api/app/infra/remote_gateway.py` defines `RemoteGateway`, the lifecycle behind Remote mode. `POST /api/remote-mode` calls `start()` and `stop()`, which return at once.

### The state machine

It runs off, then `starting`, then `ready` or `failed`. `starting` has a `step`: `docker`, `frontend` or `gateway`. `failed` has a `reason`, shown for 30 s. `/api/meta.remote_mode` reports `{enabled, expires_at, state, step, reason}`.

### The gate and the timer

Only at `ready` does it open the access gate above and start the **8-hour** timer.

These close the gate and run `docker compose down`:

- turning off
- the timer
- a failure
- a newer `start()`

It stops the frontend only if it started it.

### Testing seam

It knows nothing about HTTP. Everything touching the machine goes through a `System` object. That is `api/app/infra/remote_system.py`'s `RealSystem`: Docker Desktop, `docker compose`, the frontend process and port probes. Tests replace it with a fake and never run it for real.

### The sign-in QR

`GET /api/remote-mode/qr` returns the sign-in code as an SVG, plus the token-free address and the expiry. Local requests only. 409 unless `ready`.

## Open repo

`POST /api/sessions/{id}/open-repo` shells out to `hooks/scripts/Open-ClaudeRepoWindow.ps1`. It uses `OPEN_REPO_SCRIPT` in `api/app/routers/sessions.py`, with `subprocess.run`, and the script unmodified. It passes a `claudecode://open?path=<url-encoded cwd>` URI.

The script is the repo's own copy, not the one installed under `%USERPROFILE%\.claude\hooks\`. So `api/` now depends on that file in `hooks/`, even though `hooks/` is otherwise standalone. It needs no install step, only that the API run from this checkout.
