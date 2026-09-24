## Context

See proposal.md - Why. Two relevant pieces of existing state:

- `~/.claude/sessions/<pid>.json` (read by `claude_sessions.py`) is Claude Code's own live session
  registry. It has a `messagingSocketPath` (a named pipe) plus `peerProtocol`/`peerFeatures` fields —
  almost certainly the private IPC channel Anthropic's own integrations (e.g. the VS Code extension)
  use to talk to a running session. It's undocumented, lives inside a compiled binary, and carries no
  stability guarantee. **Rejected** as a mechanism here for exactly that reason — see Decisions.
- The existing `Notification`/`Stop` hooks (`hooks/scripts/Send-ClaudeToast.ps1`) already fire exactly
  when Claude Code needs input or finishes, including the "needs your permission" case. They're
  fire-and-forget: by the time `Notification` fires, Claude Code is already blocked on raw local
  terminal input with no external channel back into that wait. They can observe a decision is
  happening, never answer it.

## Goals / Non-Goals

**Goals:**
- Let a live session's genuine tool-permission prompt be approved or denied from another device.
- Let a live session's repo be opened in the user's editor from another device.
- Never change a session's local behavior when the relay hook isn't installed, or when nobody is
  actively watching that session's control view remotely.
- Since this change adds new remote-triggerable actions, tighten the two areas of existing exposure
  it sits next to: delete actions become local-only regardless of token, and the gateway's LAN hop
  becomes encrypted.

**Non-Goals:**
- Answering `AskUserQuestion`-style multi-choice prompts (explicitly scoped out — see proposal
  discussion; a `PreToolUse` allow/deny can't supply that tool's actual return value, only gate it).
- Replicating Claude Code's own permission-rule engine. The hook's tool matcher is a curated,
  user-adjustable guess at which tools commonly need permission, not a derivation of the user's actual
  settings.
- Real-time push. This stays polling-based, consistent with the rest of the app (`useLive`'s 2s poll,
  `LiveSnapshot`'s TTL coalescing).
- Non-Windows support for the relay hook — PowerShell only, matching every other file in `hooks/`.

## Decisions

### Mechanism: `PreToolUse` hook, not the messaging socket, not `Notification`
`PreToolUse` is the only documented Claude Code hook that can actually supply a decision
(`hookSpecificOutput.permissionDecision: "allow" | "deny"`) rather than merely observe one. It fires
before Claude Code's own permission check, for every tool call matched by the hook's `matcher` — it
has no way to know in advance whether a given call would have needed a prompt at all.

**Critical correctness point**: when the hook has no answer (nobody watching, or the wait timed out),
it must emit **no `permissionDecision` at all** (empty stdout / no hook-specific output), not
`"ask"`. `"ask"` is itself a decision that forces the interactive prompt even for a tool call that
would otherwise have been silently pre-allowed — using it as the "no answer" fallback would mean
simply having this hook installed nags the local user with prompts that used to be silent, which
directly violates the "never changes local behavior" goal. Omitting the field lets Claude Code's own
permission system decide exactly as if the hook weren't there: silent-allow if pre-approved, its
normal local prompt otherwise.

### Curated default matcher, not `*`
Every `PreToolUse` invocation spawns a PowerShell process (~100-300ms) before any network call even
happens — that's the dominant cost, not the loopback HTTP round trip. Matching every tool would tax
every tool call in every session with the hook installed, including ones that were always going to be
silently allowed. The installer registers a curated default matcher —
`Bash|Edit|MultiEdit|Write|WebFetch` — covering the tools that most commonly need permission. It's
ordinary Claude Code hook config, so the user can widen or narrow it by hand in `settings.json`
afterward; the app doesn't try to keep it in sync with actual permission rules.

### "Is anyone watching" gate, not a blind blocking wait
Even with a curated matcher, a matched tool can already be pre-allowed for a session (e.g. "don't ask
again" was chosen earlier). Blocking every matched call for a long timeout regardless would regress
those instant, already-allowed calls into slow ones. Instead:

1. The hook's single request to `api/` first checks whether *this session's* control view is
   currently open in any browser — tracked as a short-lived heartbeat (see below), not a dedicated
   "watch" call: the control view's own poll of the pending-decision endpoint doubles as the
   heartbeat.
2. **Not watched** → `api/` replies immediately (no artificial delay) with "no opinion." An unwatched
   session behaves exactly as it does today, modulo the fixed per-call hook-spawn cost.
3. **Watched** → `api/` registers the pending decision (so the control view's next poll shows it) and
   blocks the hook's request for up to a configurable timeout (default 120s) waiting for an answer.
   Unanswered by then, it replies "no opinion" too — never `"ask"` — so an ignored decision falls back
   to the session's normal local prompt instead of hanging indefinitely.

This bounds the cost precisely to "you left a session's control view open, and a matched tool call
happened while you weren't fast enough to answer it" — a cost the user opts into by having that view
open, not one every session pays. It's flagged in Risks below since it's still a real, noticeable
pause in that specific situation.

### Endpoints and data model
- `api/pending_decisions.py` — new in-memory module, lock-guarded, mirroring `live_snapshot.py`'s
  pattern: per-session `{tool_name, tool_input, created_at, asyncio.Event, answer}`, plus a
  `last_watched: dict[session_id, float]` heartbeat map.
- `GET /api/live` — each session gains `pending_decision: {tool_name, tool_input} | null`, so the
  Live list can badge a session before its control view is even opened.
- `GET /api/sessions/{id}/pending-decision` — polled every ~1-2s by the control view while mounted;
  doubles as that session's heartbeat for the "is anyone watching" gate.
- `POST /api/sessions/{id}/decisions` — called by the relay hook only (a local request; no token
  needed under the existing local-bypass rule). Body: `{tool_name, tool_input}`. Implements the gate
  described above; responds `{decision: "allow" | "deny" | null, reason: string | null}`.
- `POST /api/sessions/{id}/decisions/answer` — called by the browser (token + `X-Requested-With`
  required, like every other non-GET). Body: `{decision: "allow" | "deny", reason?: string}`. Resolves
  the pending `Event`; `409` if nothing is pending any more (already answered or timed out), so the UI
  can say "too late."
- `POST /api/sessions/{id}/open-repo` — called by the browser (token-gated). Resolves the session's
  `cwd` server-side from the live registry, the same "never from a request parameter" rule the
  `DELETE /api/sessions/{id}` route already follows, then runs
  `hooks/scripts/Open-ClaudeRepoWindow.ps1 "claudecode://open?path=<encoded cwd>"` via `subprocess`,
  unmodified. This calls the repo's own copy of the script (not the one installed under
  `%USERPROFILE%\.claude\hooks\`), so it needs no separate install step — it only requires `api/` to
  be running from this checkout, which is already always true.

### Relay hook script and its install path
`hooks/ledgerScripts/Relay-PreToolUse.ps1` — new folder, sibling to `hooks/scripts/`, holding only
hook scripts that are inherently coupled to this dashboard (as opposed to `hooks/scripts/`, which
stays the standalone toast utility). It reads the `PreToolUse` payload from stdin, reads
`$env:LEDGER_PORT` (default 8501, matching `api/server.py`'s own default), and POSTs to
`http://127.0.0.1:<port>/api/sessions/<id>/decisions` with a client-side timeout a few seconds longer
than the server's own wait. Any failure to connect (backend not running) is treated identically to "no
opinion" — empty stdout, immediately, no retry.

`Install-ClaudeHooks.ps1` gains a switch (e.g. `-IncludeSessionControl`) that additionally copies
`hooks/ledgerScripts/` into `%USERPROFILE%\.claude\hooks\ledgerScripts\` and merges the `PreToolUse`
hook entry into `settings.json`, independent of whether the toast hooks are also being
installed/already installed. `Uninstall-ClaudeHooks.ps1` gets the matching switch, removing only that
entry (matched by its script path, the same way the existing uninstall matches
`Send-ClaudeToast.ps1`). `hooks/README.md` documents this as a clearly optional second install.

### Delete requires locality, not just a token
`api/security.py`'s middleware already computes, per request, whether it's local (loopback address,
no forwarded-for marker) to decide whether a token is even required. Both `DELETE` routes
(`/api/sessions/{id}`, `/api/projects`) now additionally require that same `is_local` determination
to be true, independent of whether a valid token was presented — a token widens what a remote device
can read and trigger, but it no longer authorizes a delete. This is implemented as an extra check in
each delete route (reusing the middleware's existing locality test rather than duplicating it),
returning the same unauthorized/refused shape the token check already uses.

`GET /api/meta` gains an `is_local: bool` field, computed the same way, so the frontend can hide both
delete controls (`SessionDialog`'s `DeleteControls`, `ProjectsList`'s delete-row flow) proactively
rather than only discovering a delete is refused after trying it. The backend check is the actual
authorization boundary; hiding the buttons is UX, not the security control — consistent with how a
live session's delete control is already hidden today (`web-dashboard`'s "Sessions can be deleted,
but not live ones") while the server also independently refuses a direct request for one.

### Gateway terminates TLS with a self-signed certificate, replacing HTTP entirely
The gateway container generates (or is built with) a self-signed certificate and key, and Nginx
listens on HTTPS only — the existing plain-HTTP `server` block is replaced, not supplemented, so
there's no unencrypted fallback a client could be downgraded to. The API and frontend stay plain HTTP
behind it: they're already loopback-only and reachable only via `host.docker.internal` from inside
the gateway container, so the only network-reachable hop — gateway to another device — is the one
that needed encrypting, and it's now the only one that's on the network at all.

`GATEWAY_PORT` (default `8080`) now fronts HTTPS instead of HTTP; nothing about port selection or the
`.env` precedence changes. `api/gateway_signin.py`'s printed link and QR code switch from `http://` to
`https://`. Since the certificate is self-signed (no public CA — there's no stable hostname to get one
for on a LAN), every browser will show a one-time trust warning on first visit to a given device,
which the user accepts once, same as accepting a new token already requires opening a link. This is
called out explicitly in the modified `network-access` startup-banner requirement so it isn't mistaken
for a misconfiguration.

## Risks / Trade-offs

- **Matched tool calls pause while a control view is left open and unanswered** → up to the configured
  timeout (default 120s) per call. Mitigated by keeping the default matcher curated rather than `*`,
  by the 120s default being short enough to notice and fix if it's a problem, and by the fact that
  closing the control view immediately reverts a session to today's unaffected behavior.
- **Every matched tool call costs a PowerShell spawn (~100-300ms) whenever the hook is installed** →
  this is why it's independently installable/uninstallable rather than bundled into the toast hooks;
  the user can leave it uninstalled except during sessions where they actually want remote monitoring.
- **The faster-seeming `messagingSocketPath` IPC was deliberately not used** → recorded here so it
  isn't "discovered" and adopted later without the stability caveat: it's an undocumented, internal
  wire protocol inside a compiled binary with no versioning guarantee.
- **Race between an answer and a timeout landing at the same moment** → `POST .../decisions/answer`
  returns `409` if the pending entry is already gone; the control view shows that the session already
  moved on without this answer.
- **Two browsers with the same session's control view open** → last answer to reach the server wins;
  no locking, consistent with the app's existing assumptions elsewhere (e.g. concurrent deletes).
- **A remote device with a valid token can no longer delete anything** → this is the intended
  behavior change, not a bug, but it's a real capability loss for anyone who relied on deleting from
  a phone. Recorded here so it isn't "fixed" by accident later without revisiting the decision.
- **Self-signed certificate means a trust warning on every new device** → unavoidable without a real
  CA for a LAN address; mitigated by the startup banner explicitly saying to expect and accept it, the
  same way it already explains the token.
- **Bookmarked `http://` gateway links stop working once HTTPS replaces HTTP** → anyone with an old
  sign-in link bookmarked needs a fresh one after this ships; called out in the Migration Plan below.

## Migration Plan

Purely additive for the remote-session-control capability itself — no data migration, no changes to
existing endpoints' behavior. Existing sessions and already-installed toast hooks are unaffected until
the user explicitly opts into the new hook via the installer.

The delete-locality and gateway-HTTPS changes are not purely additive: an already-bookmarked
`http://<address>:<port>/?token=...` link stops working once the gateway switches to HTTPS-only (the
user re-runs `Start-Gateway.ps1`/opens the freshly printed `https://` link), and a workflow that
deleted sessions/projects from a phone or other remote device stops working entirely, by design.
