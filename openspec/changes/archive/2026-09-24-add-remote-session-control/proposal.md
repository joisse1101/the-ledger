## Why

The Ledger can only watch live Claude Code sessions today, not act on them. The most common reason
to walk back to the PC is that a session is blocked waiting on you: a tool-permission dialog, or a
multiple-choice question Claude asked. If you're away from the PC with a session running, it sits
idle until you return. This change lets you answer those blocking prompts from the dashboard, on the
PC or from a secondary device such as a phone, so the session continues, and also lets you jump to
that repo's VS Code window. Adding remote-triggerable actions is also the right moment to close two
gaps in what is already exposed to another device: today a remote device with the access token can
delete a session or project outright, and the gateway's LAN hop is plain HTTP, so the token itself
travels unencrypted.

## What Changes

- New optional `PermissionRequest` hook (`hooks/ledgerScripts/`). Claude Code fires this event only
  when a dialog is about to be shown to the user (a tool-permission prompt, or a question), and runs
  it alongside the terminal dialog rather than in front of it, so the dialog is never hidden or
  delayed. The hook registers the prompt with `api/` and waits; if the dashboard answers first, it
  hands that answer back to Claude Code (allow, allow with the chosen answers for a question, or
  deny with a message Claude sees). Whichever surface answers first wins: the terminal dialog, the
  dashboard on the PC, or the dashboard on another device. If nothing answers through the hook, or
  `api/` is unreachable, the hook prints nothing and the terminal dialog is simply the only way to
  answer, exactly as without the hook. This replaces the earlier `PreToolUse`-based design (a curated
  tool matcher plus an "is the control view open" heartbeat), which fired on every tool call and
  could not answer questions.
- New **Remote mode** switch: an explicit, in-memory on/off state the user turns on before leaving
  the PC. It gates only non-local devices: while it is on, another device can see a session's pending
  prompt and answer it; while it is off, another device sees no pending prompt and any attempt to
  answer is refused, while the PC's own browser and the terminal keep working. It turns itself off
  after 8 hours and after any backend restart. Only a request from the machine running the app can
  change it; other devices can see its state but not flip it.
- New `api/` in-memory pending-prompt store (ephemeral, like `LiveSnapshot`) and endpoints: one for
  the hook to register a prompt and wait, one for the dashboard to answer it, one for the local UI to
  read/set Remote mode. The live session payload gains a `pending_decision` field (the tool name and
  its input, including a question's options) so the UI can show it. Because the hook is not stopped
  when the prompt is answered elsewhere, `api/` watches the session's transcript and clears a
  pending prompt as soon as the session moves on (with a maximum age as a backstop), releasing the
  waiting hook so it exits.
- New `api/` endpoint that opens the session's repo in VS Code on the host machine, by invoking
  `hooks/scripts/Open-ClaudeRepoWindow.ps1` with a `claudecode://open?path=<cwd>` URI built from the
  session's own `cwd`, with no changes to that script.
- `SessionDialog`: selecting a session from the **Live list** now opens a control-only view instead
  of the token/context detail view: the pending prompt when there is one (Yes/No, with an optional
  reason on No, for a permission prompt; the real options, multi-select and free-text for a
  question) and an "Open repo window" button. The Live list row also shows a waiting badge while a
  prompt is pending, and the Live list itself carries the Remote mode switch (a switch on the machine
  running the app, read-only text on other devices). Selecting from the **All list** is unchanged,
  even for a session that happens to be live.
- `Install-ClaudeHooks.ps1` / `Uninstall-ClaudeHooks.ps1` gain an option to install/uninstall the
  relay hook independently of the toast hooks, and the installer also removes the legacy
  `PreToolUse` relay entry from `settings.json` if present; `hooks/README.md` documents it as
  optional.
- CLAUDE.md updated: `hooks/` no longer described as purely standalone, and `api/`'s dependency on
  `hooks/scripts/Open-ClaudeRepoWindow.ps1` for the open-repo action is documented.
- Deleting a session or project now requires a local request: a valid access token no longer makes a
  remote delete legal, enforced in `api/`'s delete routes and reflected in the frontend by hiding both
  delete controls on a non-local device. The same local-only rule protects the Remote mode switch.
  `GET /api/meta` gains an `is_local` field for the frontend to key both off of.
- The gateway now serves HTTPS only, via a self-signed certificate, replacing its plain-HTTP listener
  outright; the backend and frontend behind it stay plain HTTP since they're loopback-only regardless.
  The printed sign-in link/QR switch from `http://` to `https://`, and a browser shows a one-time
  trust warning for the self-signed certificate.

## Capabilities

### New Capabilities
- `remote-session-control`: answering a live session's blocking prompts (tool permission and
  multiple-choice questions) from the dashboard, on the PC or, while Remote mode is on, from another
  device, and opening that session's repo in VS Code on the host machine, both from the Live list's
  session view.

### Modified Capabilities
- `web-dashboard`: selecting a session from the Live list opens the new control view instead of the
  token/context detail view (the All list's detail view is unchanged); the Remote mode switch is
  shown only on the machine running the app; both delete controls are hidden on a non-local device.
- `network-access`: the token/CSRF rules that already gate data endpoints extend to the prompt-answer
  and open-repo-window endpoints; delete actions and the Remote mode switch move to a stricter
  local-only rule independent of the token, and a non-local device may see or answer a prompt only
  while Remote mode is on; the gateway's startup banner and TLS behavior are updated for HTTPS.

## Impact

- `api/`: new pending-prompt module (including transcript-based clearing) and Remote mode state +
  routes in `server.py`, `live_snapshot.py`'s payload gains `pending_decision`, new open-repo route,
  both delete routes and the Remote mode toggle gain a locality check, `/api/meta` gains `is_local`.
- `hooks/`: new `hooks/ledgerScripts/` `PermissionRequest` relay script, `Install-ClaudeHooks.ps1` /
  `Uninstall-ClaudeHooks.ps1` gain an optional-hook toggle plus removal of the legacy `PreToolUse`
  entry, `README.md` updated.
- `web/`: `SessionDialog.tsx` (new control view: prompt renderer, open-repo button; delete control
  hidden when remote), `LiveList.tsx` (waiting badge, Remote mode switch), `ProjectsList.tsx`
  (delete control hidden when remote), `api/queries.ts`, `api/types.ts`.
- `gateway/`: self-signed certificate generation, Nginx config switches to an HTTPS-only listener,
  `Dockerfile`/`docker-compose.yml` updated accordingly, `api/gateway_signin.py`'s printed link/QR
  switch to `https://`.
- `CLAUDE.md`: `hooks/` and `api/` sections updated for the new cross-folder dependency; endpoint
  table and `gateway/` section updated for the locality check, `is_local`, Remote mode, and HTTPS.
