## Context

See proposal.md - Why. Relevant existing state:

- `~/.claude/sessions/<pid>.json` (read by `claude_sessions.py`) is Claude Code's own live session
  registry. It has a `messagingSocketPath` (a named pipe) plus `peerProtocol`/`peerFeatures` fields -
  almost certainly the private IPC channel Anthropic's own integrations (e.g. the VS Code extension)
  use to talk to a running session. It's undocumented, lives inside a compiled binary, and carries no
  stability guarantee. **Rejected** as a mechanism here for exactly that reason - see Decisions.
- The existing `Notification`/`Stop` hooks (`hooks/scripts/Send-ClaudeToast.ps1`) fire when Claude
  Code needs input or finishes. They're fire-and-forget: they can observe that a decision is
  happening, never answer it.
- Claude Code's `PermissionRequest` hook event fires only when a dialog is about to be shown to the
  user. Its behavior was verified against the installed Claude Code (2.1.281), by reading its
  bundled schema and by throwaway spikes run in a live session in manual permission mode:
  - It fires for tool-permission dialogs and for `AskUserQuestion` (that tool always asks).
  - It runs **alongside** the terminal dialog, not in front of it: the dialog appeared immediately
    and a human answered it in the terminal while a hook was still waiting.
  - A hook can answer: `hookSpecificOutput.decision` is `{behavior: "allow", updatedInput?}` or
    `{behavior: "deny", message?, interrupt?}`. For `AskUserQuestion`, allow with
    `updatedInput = {...original tool_input, answers: {"<question text>": "<label or free text>"},
    annotations: {}}` produced exactly the answer, including a non-first option. This is the same
    shape the terminal dialog itself returns when a person answers.
  - A deny with a `message` blocks a Bash call and Claude receives the message.
  - The hook is **not** stopped when the dialog is answered some other way: it ran to its own
    timeout after the terminal answer, so a hook cannot rely on being killed to learn it lost.
  - Its stdin carries `session_id`, `cwd`, `transcript_path`, `permission_mode`, `tool_name`,
    `tool_input` and (for tools) `permission_suggestions`, but no per-tool-call id.

## Goals / Non-Goals

**Goals:**
- Let a live session's blocking prompts (tool-permission dialogs and `AskUserQuestion` questions) be
  answered from the dashboard: on the PC at any time, and from another device while Remote mode is on.
- Let a live session's repo be opened in the user's editor from another device.
- Never change what happens in the terminal: the local dialog is always shown and always answerable,
  with or without the hook, with the backend up or down, with Remote mode on or off.
- Since this change adds new remote-triggerable actions, tighten the two areas of existing exposure
  it sits next to: delete actions become local-only regardless of token, and the gateway's LAN hop
  becomes encrypted.

**Non-Goals:**
- Prompt kinds beyond tool permission and `AskUserQuestion`. Plan approval (`ExitPlanMode`) was not
  tested; if it reaches the hook it is shown as a generic allow/deny prompt.
- Replicating Claude Code's permission-rule engine. The hook fires only when a dialog will actually
  show, so nothing needs to guess which calls need permission.
- Telling you a prompt is waiting when a phone tab is asleep (push notifications). The toast hooks
  still fire on the PC; a phone-side alert is a separate problem.
- Detecting "away from the PC" automatically. Remote mode is an explicit switch.
- Real-time push. This stays polling-based, consistent with the rest of the app (`useLive`'s 2s poll,
  `LiveSnapshot`'s TTL coalescing).
- Non-Windows support for the relay hook - PowerShell only, matching every other file in `hooks/`.

## Decisions

### Mechanism: a `PermissionRequest` hook, not the messaging socket, not `Notification`
`PermissionRequest` is the documented hook event that fires exactly when the user is about to be
asked, and it can supply the answer. The hook registers the prompt with `api/` and waits; the
dashboard's answer, if it comes first, is handed back to Claude Code as the decision. Whichever
answer arrives first - terminal, PC dashboard, other device - wins, and Claude Code discards a
hook result that arrives after the dialog was already resolved.

**Critical correctness point**: when the hook has no answer (no answer in time, or `api/`
unreachable), it must emit **nothing at all** (empty stdout, exit 0). Any output is a decision.
Silence leaves the terminal dialog as the only way to answer, exactly as if the hook weren't
installed.

### The `PreToolUse` relay is dropped
The first version of this change used a `PreToolUse` hook (matcher `Bash|Edit|MultiEdit|Write|
WebFetch`, allow/deny, a heartbeat gate). It is removed, not kept alongside: it did not do what was
wanted. It could only gate a tool call, never supply the answer to a question, so `AskUserQuestion`
was out of its reach. It fired on every matched call and could not tell whether a dialog would
appear, which forced a curated matcher, a per-call PowerShell spawn tax, an "is anyone watching"
heartbeat, and a rule to never emit `"ask"`. All of that machinery worked around the wrong trigger.
The installer removes a previously installed `PreToolUse` relay entry; nothing in the new design
depends on it.

### Remote mode gates other devices, not the hook
Because the hook never hides the terminal dialog, it can always register the prompt - holding costs
one idle PowerShell process per open dialog, and no user-visible delay. So Remote mode is purely an
access gate on the API:

- An explicit, in-memory switch turned on before leaving the PC. Off after 8 hours and after any
  backend restart.
- **Off**: a non-local request sees no pending prompt (omitted from `GET /api/live`, empty from the
  pending-prompt route) and its answer request is refused. A local request (the PC's own browser)
  sees and answers prompts as normal.
- **On**: a non-local request that passes the normal token rules can see and answer prompts.
- Only a **local** request can change it. Other devices can read its state but not flip it, using the
  same locality test as deletes. `GET /api/meta` gains a `remote_mode` field (enabled, expires_at)
  alongside `is_local`; `POST /api/remote-mode` sets it and is local-only.

### Prompt kinds and answer shapes
The hook forwards `{tool_name, tool_input}` and the API stores it as a pending prompt. It is a
question when `tool_name` is `AskUserQuestion` (its `tool_input.questions[]` supplies question text,
options and `multiSelect`); anything else is a permission prompt. The dashboard's answer is one of:

- `{decision: "allow"}` - permission prompt approved.
- `{decision: "deny", reason?}` - permission prompt denied; the reason reaches Claude as the message.
- `{decision: "answer", answers: {"<question text>": string | string[]}}` - a question answered:
  an option label, free text, or an array for multi-select.

The hook turns these into the `PermissionRequest` decision. For a question it builds
`updatedInput = {...tool_input, answers, annotations: {}}`.

### Arbitration and clearing
Each registered prompt gets an API-generated id (Claude Code supplies none), and dashboard answers
name that id, so two prompts open at once can't be answered for each other. First answer wins:

- **Dashboard answers first**: the hook's waiting request is resolved with the answer; the prompt
  is removed.
- **Terminal answers first**: the API never hears directly, and the hook keeps running. The API
  detects it from the session's transcript: the first `user` line (the tool result) written after
  the prompt was registered means the session moved on. Only `user` lines count: `assistant` and
  bookkeeping lines (`attachment`, `system`, ...) can be written while a dialog is still open, and
  clearing on them would drop a live prompt and make a dashboard answer `409` while the terminal
  dialog is still up. The prompt is removed and the
  waiting hook request is resolved with "no answer" so the hook exits. Checked on each live
  snapshot pass, reusing the transcript tail-reading approach of `claude_context.py`.
- **Backstop**: every pending prompt has a maximum age, equal to the hook's wait (default 30 minutes,
  adjustable), after which it is dropped and the hook exits.
- A dashboard answer for a prompt that is gone returns `409`, and the UI says the session already
  moved on.

### Endpoints and data model
- `api/pending_decisions.py` - in-memory, lock-guarded module mirroring `live_snapshot.py`'s
  pattern: per-session list of `{id, tool_name, tool_input, created_at, event, answer}`, plus the
  Remote mode state.
- `GET /api/live` - each session gains `pending_decision: {id, tool_name, tool_input} | null`
  (oldest first when several), so the Live list can badge a session before it is opened. Omitted for
  non-local requests while Remote mode is off.
- `GET /api/sessions/{id}/pending-decision` - polled every ~1-2s by the control view while mounted;
  same visibility rule.
- `POST /api/sessions/{id}/decisions` - called by the relay hook only (a local request). Body:
  `{tool_name, tool_input}`. Registers and waits; responds `{decision: "allow" | "deny" | "answer" |
  null, ...}`.
- `POST /api/sessions/{id}/decisions/{prompt_id}/answer` - called by the dashboard (token +
  `X-Requested-With` like every other non-GET; a non-local request is refused with 403 unless Remote
  mode is on). Body is one of the answer shapes above; `409` if the prompt is gone.
- `POST /api/remote-mode` - local-only; body `{enabled: bool}`.
- `POST /api/sessions/{id}/open-repo` - called by the browser (token-gated). Resolves the session's
  `cwd` server-side from the live registry, the same "never from a request parameter" rule the
  `DELETE /api/sessions/{id}` route already follows, then runs
  `hooks/scripts/Open-ClaudeRepoWindow.ps1 "claudecode://open?path=<encoded cwd>"` via `subprocess`,
  unmodified. This calls the repo's own copy of the script (not the one installed under
  `%USERPROFILE%\.claude\hooks\`), so it needs no separate install step - it only requires `api/` to
  be running from this checkout, which is already always true.

### Relay hook script and its install path
`hooks/ledgerScripts/Relay-PermissionRequest.ps1` - new folder, sibling to `hooks/scripts/`, holding
only hook scripts that are inherently coupled to this dashboard (as opposed to `hooks/scripts/`,
which stays the standalone toast utility). It reads the `PermissionRequest` payload from stdin,
reads `$env:LEDGER_PORT` (default 8501, matching `api/server.py`'s own default), does a short TCP
probe of loopback, and POSTs to `http://127.0.0.1:<port>/api/sessions/<id>/decisions` with a
client-side timeout a few seconds longer than the server's own wait. Any failure to connect (backend
not running) is treated as "no answer": empty stdout, immediately, no retry.

`Install-ClaudeHooks.ps1` gains a switch (e.g. `-IncludeSessionControl`) that additionally copies
`hooks/ledgerScripts/` into `%USERPROFILE%\.claude\hooks\ledgerScripts\`, merges the
`PermissionRequest` hook entry (empty matcher, `timeout` above the script's wait) into
`settings.json`, and removes any legacy `PreToolUse` relay entry, independent of whether the toast
hooks are also being installed/already installed. `Uninstall-ClaudeHooks.ps1` gets the matching
switch, removing only the relay entries (matched by script path, the same way the existing uninstall
matches `Send-ClaudeToast.ps1`). `hooks/README.md` documents this as a clearly optional second
install. The hook is machine-wide, so it fires for every session, not just ones shown in the
dashboard; the script relays and stays silent for anything the API doesn't want.

### Delete requires locality, not just a token
`api/security.py`'s middleware already computes, per request, whether it's local (loopback address,
no forwarded-for marker) to decide whether a token is even required. Both `DELETE` routes
(`/api/sessions/{id}`, `/api/projects`) now additionally require that same `is_local` determination
to be true, independent of whether a valid token was presented - a token widens what a remote device
can read and trigger, but it no longer authorizes a delete. The Remote mode switch uses the same
check. This is implemented as an extra check in each route (reusing the middleware's existing
locality test rather than duplicating it), returning the same unauthorized/refused shape the token
check already uses.

`GET /api/meta` gains `is_local: bool`, computed the same way, so the frontend can hide both delete
controls (`SessionDialog`'s `DeleteControls`, `ProjectsList`'s delete-row flow) and the Remote mode
switch proactively rather than only discovering a refusal after trying. The backend check is the
actual authorization boundary; hiding the buttons is UX, not the security control - consistent with
how a live session's delete control is already hidden today (`web-dashboard`'s "Sessions can be
deleted, but not live ones") while the server also independently refuses a direct request for one.

### Gateway terminates TLS with a self-signed certificate, replacing HTTP entirely
The gateway container generates (or is built with) a self-signed certificate and key, and Nginx
listens on HTTPS only - the existing plain-HTTP `server` block is replaced, not supplemented, so
there's no unencrypted fallback a client could be downgraded to. The API and frontend stay plain HTTP
behind it: they're already loopback-only and reachable only via `host.docker.internal` from inside
the gateway container, so the only network-reachable hop - gateway to another device - is the one
that needed encrypting, and it's now the only one that's on the network at all.

`GATEWAY_PORT` (default `8080`) now fronts HTTPS instead of HTTP; nothing about port selection or the
`.env` precedence changes. `api/gateway_signin.py`'s printed link and QR code switch from `http://` to
`https://`. Since the certificate is self-signed (no public CA - there's no stable hostname to get one
for on a LAN), every browser will show a one-time trust warning on first visit to a given device,
which the user accepts once, same as accepting a new token already requires opening a link. This is
called out explicitly in the modified `network-access` startup-banner requirement so it isn't mistaken
for a misconfiguration.

## Risks / Trade-offs

- **With Remote mode on, anyone holding the token on the network can approve tool runs** (including
  arbitrary Bash) or answer questions. Mitigated by the token, HTTPS, the explicit switch (which only
  the PC can flip), and its 8-hour expiry; recorded so it isn't widened casually later.
- **A hook keeps running after the prompt was answered elsewhere** -> the API clears the prompt from
  the transcript signal, releases the hook, and caps every prompt's age. A stale prompt can still show
  for a few seconds on a phone; answering it returns `409` and the UI says the session moved on.
- **Behavior relies on Claude Code internals verified only on 2.1.281** (the hook running alongside
  the dialog, `updatedInput.answers` for `AskUserQuestion`, a late hook result being discarded).
  Verified by spike and the bundled schema, not the public docs. If a future version changes it, the
  worst case is that the terminal remains the only way to answer; the hook never blocks it. The tasks
  include re-verifying on each Claude Code upgrade.
- **Untested edges**: free-text "Other" answers, multi-select answers from the dashboard, plan
  approval, a late dashboard answer arriving after a terminal answer, and two prompts open at once
  (an unexplained miss was seen once when a deny and an allow ran in the same parallel batch). Each
  has an explicit verification task.
- **The faster-seeming `messagingSocketPath` IPC was deliberately not used** -> recorded here so it
  isn't "discovered" and adopted later without the stability caveat: it's an undocumented, internal
  wire protocol inside a compiled binary with no versioning guarantee.
- **Hidden phone tabs stop polling** -> a prompt can wait unseen. Push notifications are out of
  scope; the PC toast still fires.
- **Forgetting to turn Remote mode on** -> the phone sees nothing, and only the PC can turn it on.
  Intentional; recorded so it isn't "fixed" by letting other devices flip the switch.
- **A remote device with a valid token can no longer delete anything** -> intended behavior change,
  not a bug, but a real capability loss for anyone who relied on deleting from a phone. Recorded so
  it isn't "fixed" by accident later without revisiting the decision.
- **Self-signed certificate means a trust warning on every new device** -> unavoidable without a real
  CA for a LAN address; mitigated by the startup banner explicitly saying to expect and accept it, the
  same way it already explains the token.
- **Bookmarked `http://` gateway links stop working once HTTPS replaces HTTP** -> anyone with an old
  sign-in link bookmarked needs a fresh one after this ships; called out in the Migration Plan below.

## Migration Plan

Additive for the remote-session-control capability itself - no data migration, no changes to
existing endpoints' behavior. Existing sessions and already-installed toast hooks are unaffected
until the user opts into the new hook via the installer. A machine that installed the earlier
`PreToolUse` relay gets it removed by the installer (or by re-running the uninstaller for it); until
then that entry can still hold matched tool calls, so it should be removed before relying on this.

The delete-locality and gateway-HTTPS changes are not purely additive: an already-bookmarked
`http://<address>:<port>/?token=...` link stops working once the gateway switches to HTTPS-only (the
user re-runs `Start-Gateway.ps1`/opens the freshly printed `https://` link), and a workflow that
deleted sessions/projects from a phone or other remote device stops working entirely, by design.
