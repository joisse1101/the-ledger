## Context

See proposal.md for motivation. Current state that shapes the approach:

- `PendingDecisions` (`api/app/domain/pending_decisions.py`) is the lock-guarded, in-memory store of
  pending prompts and the Remote-mode gate. The relay hook's `POST /api/sessions/{id}/decisions`
  reaches `request_decision()`, which `register()`s the prompt and waits for `answer()`.
- Answers already validate in `decision_service`: a non-`AskUserQuestion` prompt takes
  `{decision: "allow"}`. `AskUserQuestion` is the only tool the code treats as a question today.
- `/api/live` rows are built by `prompt_service.live_with_prompts` (adds `pending_decision`);
  `/api/meta` already carries `is_local` and `remote_mode`. Local-only switches (Remote mode, delete)
  check `is_local` in the route.
- The widget talks to the backend over loopback, polls `/api/live` and `/api/meta`, renders each row
  as a `<button class="row">` that opens the repo window, and has no write action on a row today.
  The Live list's `columns` array in `LiveList.tsx` is a static module constant.

## Goals / Non-Goals

**Goals:**
- Approval happens in the backend, so it works with no UI open and without a polling delay.
- Exactly one place decides what counts as "plain": a single predicate, easy to tighten later.
- Both UIs only flip a flag and render state; neither contains approval logic.

**Non-Goals:**
- No user-configurable pattern list or per-tool allowlist, no persistence across a backend restart, no history beyond the
  latest auto-approved prompt, and no auto-deny. YAGNI until a second real use asks for it.
- No change to the relay hook script or the installer.
- No remote-device control of the switch.

## Decisions

**1. Flag and unlock state live in `PendingDecisions`, next to the prompts.**
New fields behind the existing lock: `_auto_approve: dict[session_id, expires_monotonic]`,
`_last_auto_approved: dict[session_id, {tool_name, at}]`, and `_relay_hook_seen: bool`.
`register()` sets `_relay_hook_seen` (the relay hook is the only caller). Methods:
`set_auto_approve(session_id, enabled)`, `auto_approve_enabled(session_id)` (expires lazily, like
`_remote_enabled`), `last_auto_approved(session_id)`, `relay_hook_seen()`,
`prune_auto_approve(live_session_ids)`.
Alternative: a second store class. Rejected: the prompt list and the flag must be read under one lock
to avoid a race (decision 3), and the file already mirrors `LiveSnapshot`'s pattern.

**2. Approval is applied in the backend at registration, not by a client.**
`request_decision()` calls `register()`, then, if the session's flag is on and
`is_auto_approvable(tool_name, tool_input)` holds, calls the existing `answer()` with `{decision: "allow"}`
and records `_last_auto_approved`. The hook's request then returns immediately.
Alternative: the UIs poll and click Approve. Rejected: needs a UI open, adds up to a poll interval of
delay, and would duplicate the logic in two clients.

**3. Switching on also drains what is already pending.**
`auto_approve_service.set_enabled()` sets the flag, then walks `for_session()` and answers each plain
prompt. Register-then-check-flag and set-flag-then-scan-pending cover both orders of a race between a
new prompt and the toggle; a prompt reached by both is answered once because `answer()` returns False
for a prompt that is already gone. This is an idempotent operation.

**4. One predicate defines "plain" and "safe to auto-approve".**
A pure function `is_auto_approvable(tool_name, tool_input)` in a new domain module
(`api/app/domain/auto_approve_policy.py`, no I/O). It returns false when the tool is in
`{AskUserQuestion, ExitPlanMode}`. For the shell tools (`Bash`, `PowerShell`) it reads
`tool_input["command"]` and returns false when that is missing, not a string, or matches any pattern
in a module-level tuple of precompiled case-insensitive regexes (`DANGEROUS_COMMAND_PATTERNS`);
the check fails closed. Starting patterns, to be tuned in review: `sudo`/`su`/`doas`/`runas`,
`rm` with `-r`/`-f` flags, `Remove-Item` with `-Recurse` or `-Force`, `del /s`/`rmdir /s`/`rd /s`,
`git push` with `--force`/`-f`, `git reset --hard`, `git clean -f`, `curl`/`wget`/`iwr`/`irm`
piped to a shell or `iex`/`Invoke-Expression`, `mkfs`/`format`/`diskpart`/`dd of=`,
`chmod`/`chown -R`, `shutdown`/`reboot`/`Restart-Computer`, `reg delete`, and `DROP TABLE|DATABASE`.
Patterns are matched against the whole command string, so a dangerous word inside a chained command
(`a && sudo b`) is caught. `decision_service`'s `QUESTION_TOOL` constant moves down into this domain
module and is imported from there (imports point downward only).
Alternatives: judge by `tool_input` shape (rejected: tool names are the stable, documented signal and
`ExitPlanMode` is permission-shaped but multi-choice in the terminal); a user-editable pattern file
(rejected for now: YAGNI and a config schema to validate; the tuple is one place to edit later); an
allowlist of safe commands (rejected: far more upkeep, and it would pause most real work).
This denylist is a best-effort guard, not a security boundary: obfuscation, variable indirection or a
script file that holds the dangerous command can slip past a regex. Auto-approve stays opt-in for
that reason, and the docs say so.

**5. Lifetime mirrors Remote mode.**
Per-session expiry of 8 hours (a new `AUTO_APPROVE_TTL_SECONDS`, same value as the Remote TTL),
memory only, so a backend restart clears it. `prune_auto_approve()` runs inside
`prompt_service.live_with_prompts`, which already runs on each `/api/live` read, dropping flags and
audit entries for sessions no longer in the live list.
Alternative: keep flags until restart. Rejected: a stale flag could apply to nothing now but would
linger, and the TTL is the guard against a forgotten switch.

**6. API surface.**
- `POST /api/sessions/{id}/auto-approve` with body `{enabled: bool}`, returns `{auto_approve: bool}`.
  The route checks `is_local` and returns 403 otherwise (same as `/api/remote-mode`); the service
  raises `NotFound`/`Conflict` for a session that is not live.
- `/api/live` rows gain `auto_approve: bool` and `last_auto_approved: {tool_name, at} | null`. They
  are shown to every client that can see the list; only the switch is local-only.
- `/api/meta` gains `relay_hook_seen: bool`. `routers/meta.py` may not import `deps`, so it reads it
  through a service function (`prompt_service.relay_hook_seen()`), as it does for `remote_mode`.
- The new `routers/auto_approve.py` and `schemas/auto_approve.py` follow the `remote_mode.py` /
  `schemas/remote.py` pattern, and the router is registered in `app/main.py`.
- Additive only; no existing field changes.

**7. Where the UIs get the unlock state.**
Both read `relay_hook_seen` from `/api/meta` (the widget already polls meta for Remote mode; the web
app already has `useMeta`). Auto-approve controls render only when it is true. The web switch
additionally requires `meta.is_local`; a non-local device sees a read-only "Auto-approve on" label.

**8. Ledger UI.**
`LiveSessionPanel.tsx` renders the existing switch component beside the `<h2>` title;
`LiveControl.tsx` shows the "last auto-approved" caption. `LiveList.tsx`'s columns become a function
of `relayHookSeen` that appends the Auto-approve column (an "On" marker, empty when off) for the Live
list only. A new `useSetAutoApprove(sessionId)` mutation in `queries.ts` invalidates the live query.
The `types.ts` mirror gains the new fields.

**9. Widget UI: a sibling button, not a nested one.**
The row is currently a `<button>`; a `<button>` inside a `<button>` is invalid HTML and behaves
inconsistently. The row becomes a `div` wrapper holding the existing open-repo `<button>` (filling
the row) and the auto-approve `<button>` positioned at the right end, so it looks nested and a click
on it never reaches the open handler. Main-process `api.ts` gains `setAutoApprove(sessionId,
enabled)`, exposed through the existing IPC/preload pattern; the renderer updates from the next poll.
Existing tests that select `.row` change with the markup.

**10. Audit and logging.**
Each automatic approval is logged as a structured line (`session_id`, `tool_name`, no `tool_input`,
which can hold secrets) at the module logger, in addition to the in-memory `last_auto_approved`.

## Risks / Trade-offs

- [Auto-approving Bash/Write unattended is high blast radius] → Off by default, per session, local-only
  switch, 8-hour expiry, visible marker (list column, widget button, panel switch), audit line,
  questions and plan approval always pause, and dangerous shell commands pause via the denylist.
- [The denylist can miss an obfuscated command, or pause a harmless one such as `rm -rf node_modules`]
  → Fail-closed on unreadable commands; a false pause only costs one manual click. It is documented
  as best-effort, not a sandbox.
- [`relay_hook_seen` resets on backend restart, hiding the switch until the next prompt] → Accepted by
  design; the controls reappear on the first prompt, and a flag set before the restart is gone anyway.
- [`relay_hook_seen` is true from any registration, including a forged local one] → The registration
  route is already local-only; the worst case is showing a switch that then cannot act.
- [A prompt can be answered from the terminal at the same moment] → Existing "first answer wins"
  behavior; the loser's `answer()` returns False and nothing else happens.
- [Tool names change in Claude Code, e.g. a new multi-choice tool] → The exclusion set is one
  constant; an unknown choice-style tool would be auto-approved, so the set needs review when Claude
  Code adds prompt types.
- [`last_auto_approved` stays visible after the switch is turned off] → Acceptable: it is a record,
  and it is dropped when the session leaves the live list.

## Migration Plan

No data migration; all state is in memory and additive. Rollback is reverting the change; clients that
ignore the new fields keep working.
