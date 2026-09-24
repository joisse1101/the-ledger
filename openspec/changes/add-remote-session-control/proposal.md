## Why

The Ledger can only watch live Claude Code sessions today, not act on them. Two things force you back
to the PC even when you're already looking at the dashboard on a phone: answering a tool-permission
prompt that's blocking a live session, and jumping to that repo's VS Code window to look closer. Both
are small, well-scoped actions the host machine can already perform locally (Claude Code's own hook
system, and the existing `Open-ClaudeRepoWindow.ps1` toast-click handler) — this change exposes them
through the dashboard instead. Adding remote-triggerable actions is also the right moment to close
two gaps in what's already exposed to another device: today a remote device with the access token can
delete a session or project outright, and the gateway's LAN hop is plain HTTP, so the token itself
travels unencrypted.

## What Changes

- New optional `PreToolUse` hook (`hooks/ledgerScripts/`) that, when a live session is about to run a
  tool needing permission *and* that session's control view is currently open on another device,
  registers the pending decision with `api/` and blocks waiting for an answer. It returns `allow`/
  `deny` (+ an optional reason on deny) if the dashboard answers in time; otherwise — nobody watching,
  no answer in time, or `api/` unreachable — it hands back no decision at all, so Claude Code decides
  exactly as it would without the hook installed. This is always an additive fast path, never a
  required gate, and never turns a silent, pre-allowed tool call into one that prompts.
- New `api/` in-memory pending-decision store (ephemeral, like `LiveSnapshot`) and endpoints: one for
  the relay hook to register a decision and block on it, one for the browser to submit an answer. The
  live session payload gains a `pending_decision` field (tool name + tool input) so the UI can show it.
- New `api/` endpoint that opens the session's repo in VS Code on the host machine, by invoking
  `hooks/scripts/Open-ClaudeRepoWindow.ps1` with a `claudecode://open?path=<cwd>` URI built from the
  session's own `cwd` — no changes to that script.
- `SessionDialog`: selecting a session from the **Live list** now opens a control-only view (the
  pending decision, if any, with Approve/Deny, plus an "Open repo window" button) instead of the
  existing token/context detail view. Selecting from the **All list** is unchanged, even for a session
  that happens to be live.
- `Install-ClaudeHooks.ps1` / `Uninstall-ClaudeHooks.ps1` gain an option to install/uninstall the new
  relay hook independently of the existing toast hooks; `hooks/README.md` documents it as optional.
- CLAUDE.md updated: `hooks/` no longer described as purely standalone (it now also holds this
  dashboard-coupled, optional hook), and `api/`'s dependency on `hooks/scripts/Open-ClaudeRepoWindow.ps1`
  for the open-repo action is documented.
- Deleting a session or project now requires a local request: a valid access token no longer makes a
  remote delete legal, enforced in `api/`'s delete routes and reflected in the frontend by hiding both
  delete controls entirely on a non-local device. `GET /api/meta` gains an `is_local` field for the
  frontend to key that off of.
- The gateway now serves HTTPS only, via a self-signed certificate, replacing its current plain-HTTP
  listener outright; the backend and frontend behind it stay plain HTTP since they're loopback-only
  regardless. The printed sign-in link/QR switch from `http://` to `https://`, and a browser shows a
  one-time trust warning for the self-signed certificate.

## Capabilities

### New Capabilities
- `remote-session-control`: answering a live session's pending tool-permission decision from another
  device, and opening that session's repo in VS Code on the host machine, both from the Live list's
  session view.

### Modified Capabilities
- `web-dashboard`: selecting a session from the Live list opens the new control view instead of the
  token/context detail view (the All list's detail view is unchanged); both delete controls are
  hidden on a non-local device.
- `network-access`: the token/CSRF rules that already gate data endpoints extend to the new
  decision-answer and open-repo-window endpoints; delete actions move to a stricter local-only rule
  independent of the token; the gateway's startup banner and TLS behavior are updated for HTTPS.

## Impact

- `api/`: new pending-decision module + routes in `server.py`, `live_snapshot.py`'s payload gains a
  `pending_decision` field, new open-repo route, both delete routes gain a locality check, `/api/meta`
  gains `is_local`.
- `hooks/`: new `hooks/ledgerScripts/` relay hook script, `Install-ClaudeHooks.ps1` /
  `Uninstall-ClaudeHooks.ps1` gain an optional-hook toggle, `README.md` updated.
- `web/`: `SessionDialog.tsx` (new control view + Approve/Deny + open-repo button; delete control
  hidden when remote), `ProjectsList.tsx` (delete control hidden when remote), `api/queries.ts`,
  `api/types.ts`.
- `gateway/`: self-signed certificate generation, Nginx config switches to an HTTPS-only listener,
  `Dockerfile`/`docker-compose.yml` updated accordingly, `api/gateway_signin.py`'s printed link/QR
  switch to `https://`.
- `CLAUDE.md`: `hooks/` and `api/` sections updated to reflect the new cross-folder dependency; `api/`
  endpoint table and `gateway/` section updated for the locality check, `is_local`, and HTTPS.
