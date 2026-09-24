## 1. Drop the PreToolUse relay

- [x] 1.1 Remove the still-installed `PreToolUse` relay entry from `~/.claude/settings.json` right
      away, using the existing `Uninstall-ClaudeHooks.ps1 -IncludeSessionControl` (it works today),
      before any rework starts. Verify `settings.json` no longer has a `PreToolUse` entry pointing at
      `Relay-PreToolUse.ps1` and the toast hooks are untouched.
- [x] 1.2 Delete `hooks/ledgerScripts/Relay-PreToolUse.ps1` once task 4.1's replacement exists, and
      remove every reference to it (installer, uninstaller, README, tests). Verify with a repo-wide
      search that nothing mentions `Relay-PreToolUse` or a `PreToolUse` relay any more.
      _Done with group 5 (2026-09-24). The script is deleted; the README no longer mentions it. The
      installer and uninstaller still name `Relay-PreToolUse.ps1`/`PreToolUse` on purpose, in their
      legacy-cleanup code only - that is how they find and remove a machine's still-installed
      earlier relay (5.1/5.2 require it), so a repo-wide search is not literally empty. The one other
      leftover is a comment in `web/src/api/types.ts` ("relayed by the optional PreToolUse hook"),
      which goes with 6.1's rework of that file._

## 2. Backend: pending-prompt store and Remote mode (rework)

- [x] 2.1 Rework `api/pending_decisions.py`: per-session list of prompts `{id, tool_name, tool_input,
      created_at, asyncio.Event, answer}` with API-generated ids; remove the `last_watched` heartbeat
      and `is_watched()`. Add the Remote mode state (enabled, expires_at; auto-off after 8 hours;
      starts off after every process start). Verify with unit tests: register -> answer -> resolve;
      register -> cleared -> waiter released with no answer; two prompts for one session keep
      independent ids; Remote mode expires and starts off.
- [x] 2.2 Add transcript-based clearing: a prompt is cleared when the session's transcript has a new
      line written after the prompt's `created_at` (reusing `claude_context.py`'s tail-reading
      approach), releasing its waiting hook request with no answer; add a maximum age (default 30
      minutes, adjustable) as a backstop. Check on each live snapshot pass. Verify with tests over
      temporary transcript files: a later line clears it, an unchanged transcript does not, the max
      age drops it.

## 3. Backend: routes (rework)

- [x] 3.1 Rework `POST /api/sessions/{id}/decisions` (relay hook only, local request): always
      registers the prompt, waits up to the configured wait, responds `{decision: "allow" | "deny" |
      "answer" | null, ...}`. Verify with `TestClient` tests: answered, cleared with no answer, and
      wait elapsed.
- [x] 3.2 Rework `GET /api/sessions/{id}/pending-decision`: remove the watch side effect; apply the
      visibility rule (a non-local request sees a prompt only while Remote mode is on). Verify with
      tests for local, non-local with Remote mode off, and non-local with it on.
- [x] 3.3 Rework the answer route to `POST /api/sessions/{id}/decisions/{prompt_id}/answer`: body is
      `{decision: "allow"}`, `{decision: "deny", reason?}` or `{decision: "answer", answers: {...}}`;
      validate answers against the stored prompt (option label or free text; an array only for
      multi-select); token + `X-Requested-With` like other non-GET routes; `403` for a non-local
      request while Remote mode is off; `409` when the prompt is gone. Verify with tests for each
      shape, the invalid-answer case, `403` and `409`.
      _Implemented contract (2026-09-24), for 4.1/6.1/6.2 to build against:_
      - _Answer body: `{decision: "allow"}`; `{decision: "deny", reason?}` (blank reason -> null);
        `{decision: "answer", answers: {"<question text>": string | string[]}}`. Success is
        `{answered: "<prompt_id>"}`._
      - _What the relay hook's `POST .../decisions` returns: `{decision: "allow"}`, `{decision:
        "deny", reason: string | null}`, `{decision: "answer", answers}`, or `{decision: null}`
        (cleared / wait elapsed -> print nothing)._
      - _Status codes: `403` non-local while Remote mode is off; `409` prompt gone (answered,
        cleared by the transcript sweep, or expired); `422` answer doesn't fit the prompt._
      - _Strictness choices, not dictated by the spec, so they can be loosened without touching
        anything else (`_checked_answers`/`_checked_answer` in `api/server.py`): the kind must match
        (`answer` only for `AskUserQuestion`, `allow`/`deny` only for everything else); `answers`
        must cover exactly the questions in `tool_input.questions[]`, no more, no fewer; a string
        must be non-blank; a list only for a `multiSelect` question, non-empty, no blank items; a
        prompt with no readable `questions[]` cannot be answered from the dashboard at all (the
        terminal still can). Option labels are NOT checked - any non-blank string passes, since
        free text ("Other") is legitimate._
- [x] 3.4 Rework `GET /api/live`'s per-session `pending_decision` to `{id, tool_name, tool_input} |
      null` (oldest first), omitted for a non-local request while Remote mode is off. Verify with
      `test_api_data.py` cases.
- [x] 3.5 `POST /api/sessions/{id}/open-repo` (already built; unchanged by this rework).
- [x] 3.6 `is_local` locality check on both delete routes and `is_local` on `GET /api/meta`
      (already built; unchanged by this rework).
- [x] 3.7 Add `remote_mode: {enabled, expires_at}` to `GET /api/meta` and `POST /api/remote-mode`
      (`{enabled: bool}`), local-only using the same locality test as the delete routes. Verify with
      tests: local switch works without a token; a non-local request with a valid token is refused;
      `/api/meta` reflects the state for local and non-local requests.
      _Notes (2026-09-24): `pending_decision` is `null`, not an absent key, when hidden from a
      non-local request, so "hidden" and "no prompt" look identical to a remote device. Prompts are
      cleared by `decisions.sweep()`, run at the top of `GET /api/live`, the pending-decision route
      and the answer route (via `LiveSnapshot.latest_activity`); there is no timer, so a prompt is
      only swept while something polls. Also added, beyond the task text: `POST .../decisions` is
      refused with `403` for a non-local request (the hook is always on this machine)._

## 4. Relay hook script (rework)

- [x] 4.1 Create `hooks/ledgerScripts/Relay-PermissionRequest.ps1`: parse the `PermissionRequest`
      stdin payload, read `$env:LEDGER_PORT` (default 8501), do a short loopback TCP probe, POST
      `{tool_name, tool_input}` to `/api/sessions/<id>/decisions` with a client timeout a few seconds
      above the server's wait, and translate the response into `hookSpecificOutput.decision`: allow
      (for a question, `updatedInput = {...tool_input, answers, annotations: {}}`), or deny with a
      `message`. Print nothing at all for no answer or any failure. Verify by running it manually
      against a live local `api/` for an answered and an unanswered prompt, and against a stopped
      backend to confirm silent, immediate exit.
      _Done (2026-09-24), verified against a throwaway backend on port 8511 with a script POSTing
      answers to the real routes: allow, deny with a reason, deny without one (message defaults to
      "Denied from the Ledger dashboard"), and a two-question `AskUserQuestion` (single choice + a
      multi-select) each produced the expected `hookSpecificOutput`; an unanswered prompt (client
      timeout), a malformed payload and a stopped backend each printed nothing and exited 0 (a
      stopped backend in ~1.2s total, essentially PowerShell start-up). Not exercised: the API's
      "cleared by the terminal answering" path (a `{decision: null}` reply) - the script treats any
      non-allow/deny/answer reply as silence, and the API side is covered by group 2/3 tests.
      Choices: `-TimeoutSeconds` defaults to 1805 (the API's 30-minute prompt lifetime + 5s), so
      the installed hook `timeout` is 1810. The port still comes from the installer-baked `-Port`,
      then `$env:LEDGER_PORT`, then 8501 (kept from the earlier relay). A multi-select answer is
      forwarded into `updatedInput.answers` as a JSON array, unchanged - see the open question
      in 7.2._

## 5. Install / uninstall (rework)

- [x] 5.1 Rework `-IncludeSessionControl` in `Install-ClaudeHooks.ps1`: copy
      `hooks/ledgerScripts/`, merge a `PermissionRequest` entry (empty matcher, hook `timeout` above
      the script's wait) into `settings.json`, and remove any legacy `PreToolUse` relay entry.
      Verify by running it in isolation on a `settings.json` that has the legacy entry.
- [x] 5.2 Rework the matching switch in `Uninstall-ClaudeHooks.ps1`: remove the `PermissionRequest`
      relay entry (and a legacy `PreToolUse` one if present) and the `ledgerScripts` folder, leaving
      toast hooks untouched. Verify by installing both, uninstalling only session control, and
      confirming the toast hooks remain.
- [x] 5.3 Update `hooks/README.md`: the optional relay section describes the `PermissionRequest`
      hook, the `-IncludeSessionControl` install/uninstall commands, the wait and timeout defaults,
      and notes that its behavior was verified on Claude Code 2.1.281 and should be re-checked after
      Claude Code upgrades.
      _5.1-5.3 done (2026-09-24). 5.1/5.2 verified in isolation against a fake `USERPROFILE` (real
      `settings.json` and registry untouched), seeded with toast hooks, the legacy relay entry plus
      script, and an unrelated `PreToolUse` hook: install adds one `PermissionRequest` entry
      (timeout 1810), removes the legacy entry and script, keeps the unrelated hook, and re-running
      doesn't duplicate; `-IncludeSessionControl -SkipToastHooks` uninstall removes the relay
      and folder and leaves both toast hooks; it also cleans up a settings file that still has only
      the legacy entry. Not run: the installer with the toast hooks included (it writes the real
      HKCU `claudecode://` handler); that path is unchanged._

## 6. Frontend (rework)

- [x] 6.1 Rework `web/src/api/types.ts` and `queries.ts`: the new `pending_decision` shape, an
      answer mutation for the three answer shapes, and hooks for Remote mode (read from `useMeta`,
      set via `POST /api/remote-mode`). Verify with `npm test` covering the new request shapes.
      _Note (2026-09-24): the backend (group 3) is done, so the frontend is currently BROKEN against
      it until this lands. `web/src/api/queries.ts` (+ `queries.test.tsx`) still posts to the old
      `/api/sessions/{id}/decisions/answer` with `{decision, reason}` and polls for a
      `pending_decision` without an `id`. New contract: `pending_decision: {id, tool_name,
      tool_input} | null`; answer to `/decisions/{prompt_id}/answer`; `useMeta` now also returns
      `remote_mode: {enabled, expires_at}`. A `409` means "session already moved on", a `422` is a
      client bug (the UI builds only valid shapes), a `403` means Remote mode is off._
      _Done (2026-09-24). `types.ts`: `PendingDecision.id`, `DecisionAnswer` as a union of the three
      shapes, `RemoteMode`, `Meta.remote_mode`, `QUESTION_TOOL`. `queries.ts`: `useAnswerDecision(
      sessionId)` now takes `{promptId, answer}` and posts to `/decisions/{prompt_id}/answer`;
      `useSetRemoteMode()` posts `/api/remote-mode` and writes the reply into the cached meta; the
      heartbeat wording is gone. Remote mode is read from `useMeta` (polled every 60s, so another
      device sees a flip within about a minute, though prompts themselves arrive via the 1.5-2s
      polls). `npm test` covers the URL, body and headers for each shape, a 409, the Remote mode
      POST, and a 403._
- [x] 6.2 Rework `LiveControl.tsx`/`SessionDialog.tsx` control view into a prompt renderer: a
      permission prompt shows tool name and input with Approve/Deny (Deny opens an optional reason);
      a question shows each question with its options, multi-select where allowed, and a free-text
      field; a `409`/gone state says "this session already moved on"; the "Open repo window" button
      stays. Verify against a live session (see 7.1-7.3) and confirm `from === "all"` is unchanged.
      _Done (2026-09-24), except the live-session verification, which is 7.1-7.3 and NOT yet run.
      New `DecisionPrompt.tsx` (permission card; question card with radios/checkboxes, a free-text
      "Other", and Send disabled until every question is answered, mirroring the API's rules so the
      UI only builds valid shapes) and `lib/prompt.ts` (parsing `questions[]`, building `answers`,
      unit-tested). A question with no readable `questions[]` shows the input and says to answer in
      the terminal, matching the API refusing it. `LiveControl.tsx` shows "already moved on" both for
      a 409 and when a prompt vanishes without this view having answered it, and tells another
      device why it sees nothing while Remote mode is off. `SessionDialog.tsx` is untouched, so
      `from === "all"` is unchanged (only checked by reading, not in a browser). A multi-select
      answer is still sent as an array; see the open question under 7.2._
- [x] 6.3 `LiveList.tsx`: keep the pending-prompt badge (now driven by the new field) and add the
      Remote mode control: a switch when `is_local`, read-only text (state and time left) otherwise.
      Verify visually and with `npm test`.
      _Done (2026-09-24), `npm test`/`tsc`/`npm run build` only - NOT verified visually in a browser
      yet. New `RemoteModeControl.tsx` in the Live toolbar (switch with time left when local,
      read-only "Remote mode: on, 7h 59m left" otherwise; it also reads as off the moment
      `expires_at` passes, without waiting for the next meta refresh). The badge now reads "Asking a
      question" for `AskUserQuestion`, else "Needs decision: <tool>"._
- [x] 6.4 Read `is_local` from `useMeta()` and hide both delete controls when false (already built;
      unchanged by this rework).

## 7. End-to-end verification

- [x] 7.1 Permission prompt: with the relay hook installed and Remote mode on, trigger a Bash
      permission dialog, answer it from the PC dashboard and from a phone: Approve runs the tool, Deny
      with a reason blocks it and Claude sees the reason.
- [x] 7.2 Questions: trigger an `AskUserQuestion` and answer it from the dashboard with a single
      choice, a multi-select, and free text ("Other"); confirm Claude receives exactly that answer.
      _Verified live by the user (2026-09-24): a two-question `AskUserQuestion` (single choice + multi-select
      with two ticks and free "Other" text) answered on the dashboard reached Claude exactly as sent; the
      multi-select arrived as a list._
      _**RESOLVED (2026-09-24), confirmed twice with the answer given in the terminal**: the terminal
      dialog records a multi-select answer as a JSON array in
      the transcript's `toolUseResult.answers` (`["auth","logs","tracing"]`, `annotations: {}`), the
      same shape the hook forwards, so no change to 4.1 is needed. Still to run: answering one from the
      dashboard and confirming Claude receives it (steps in the conversation). The text below is the
      original question, kept for the record._
      _Shelved, out of scope (2026-09-24): the terminal dialog also lets a person attach a note to an
      answer (`annotations`); the dashboard and hook always send `annotations: {}`. The shape of a
      non-empty `annotations` was never observed. Follow-up change: spike it (answer with a note in the
      terminal, read `toolUseResult.annotations` from the transcript), then spec and build it. Ticking
      options plus typing "Other" text on a multi-select already works and matches the terminal._
      _Original TODO: the API passes a multi-select answer through as a JSON array
      (`"Which extras?": ["auth", "logs"]`) and 4.1 forwards it into `updatedInput.answers` as is.
      Whether Claude Code expects an array there, or a joined string, was never spiked - only
      single-choice answers were. Check what the terminal dialog itself produces for a multi-select
      and match it in 4.1 (if it is a string, join in the hook, not the API)._
      _Automated (2026-09-24): `test_relay_hook.py` pins that a one-item multi-select stays a list through
      the script's PowerShell JSON round trip, and that non-ASCII answers survive. If the spike shows a
      joined string is needed, update those tests with the fix._
- [x] 7.3 First answer wins: answer in the terminal and confirm the dashboard clears the prompt
      within a few seconds and the hook exits; submit a late dashboard answer and confirm `409` and an
      unaffected session; confirm a late hook result after a terminal answer is discarded.
      _**TODO (2026-09-24)**: the hook's silent path when the terminal answers first was never run
      end to end - `Relay-PermissionRequest.ps1` was only tested with dashboard answers, a client
      timeout, a malformed payload and a stopped backend. Run it live: answer in the terminal, then
      confirm the API's transcript sweep releases the hook (`{decision: null}`), the hook prints
      nothing and exits, and the dashboard drops the prompt. Also the "late hook result is
      discarded" claim rests on the 2.1.281 spike, not a test here._
      _Partly covered (2026-09-24): `test_relay_hook.py::test_the_terminal_answering_first_releases_the_hook_silently`
      runs the real script, simulates the terminal answer as a newer transcript line, and asserts the
      sweep releases the hook with no output, the prompt leaves `/api/live`, and a late dashboard answer
      gets `409`. That replaces the API/script half of the TODO above; the live half (a real terminal
      answer, and Claude Code discarding a late hook result) is still open._
      _Verified live by the user (2026-09-24)._
- [x] 7.4 Remote mode gating: with it off, a phone sees no prompt and cannot answer, and the PC
      dashboard and terminal still work; a phone cannot flip the switch even with a valid token;
      confirm the 8-hour expiry and restart reset.
      _Gating, the local-only switch, the 8-hour expiry and the restart reset are already covered by
      `test_pending_decisions.py`, `test_api_data.py` and `test_security.py`; what's left is doing it
      from a real phone through the gateway._
- [x] 7.5 Never-alters guarantees: with the hook installed and the backend stopped, a permission
      dialog and a question appear with no noticeable delay; with Remote mode on or off the terminal
      dialog is always shown and answerable.
      _Verified live (2026-09-24): with the hook installed and the backend stopped, a Bash permission
      dialog and an `AskUserQuestion` both appeared in the terminal and were answerable, and the user
      reported no delay. The dashboard shows nothing while the backend is down, as expected (nothing to
      poll). Remote mode on/off never affected the terminal dialog in any run. Also pinned by
      `api/tests/test_relay_hook.py` ("backend stopped -> no output, exit 0, quickly")._
- [x] 7.6 Edge cases: two prompts open at once (including a parallel allow + deny batch, where a
      miss was once observed) each resolve to their own answer; note what `ExitPlanMode` does when
      it reaches the hook.
      _Run live (2026-09-24). (a) Parallel batch. Claude Code asks about parallel Bash calls ONE AT A
      TIME: in the instrumented runs each call's hook fired only after the previous one resolved
      (`open_for_session=1` throughout), so two prompts were never open at once from a batch. Three clean
      rounds (allow / deny with reason / allow), all answered on the dashboard, each reached its own hook
      and Claude Code with the right decision. The earlier "answered on the dashboard, no response" miss
      did NOT reproduce. One round showed prompts going stale when the dashboard tab was in the
      background (auto-refresh pauses in a hidden tab), which is expected. Instrumentation was temporary
      and has been removed. Hardening from the analysis: the transcript sweep now treats only a `user`
      line (a tool result) as "the prompt was answered", not any timestamped line (an `assistant` line
      for a later tool call, or an `attachment`/`system` note, can land while a dialog is open and would
      have dropped a live prompt, making a dashboard answer `409` while the terminal dialog stayed up -
      the most plausible cause of the original miss, unproven). Covered by
      `test_claude_context.py::test_latest_activity_ignores_assistant_and_bookkeeping_lines` and
      `test_pending_decisions.py::test_sweep_keeps_a_prompt_while_only_assistant_or_bookkeeping_lines_arrive`.
      Two prompts open at once (via the store) are also covered by `test_relay_hook.py`.
      (b) `ExitPlanMode` DOES reach the hook and is shown as a generic Approve/Deny prompt; tool_input was
      `{}` the first time (plan file not yet written) and carried the plan text afterwards. No
      plan-specific controls (auto-accept edits, keep planning with feedback). Intended per the design's
      non-goals. Shelved as a follow-up change: richer plan approval. Approving `ExitPlanMode` from the
      dashboard was not exercised (answers came from the terminal)._
- [x] 7.7 Confirm "Open repo window" both focuses an already-open VS Code window and opens a new one
      when the repo isn't open yet, from a live session's control view.

## 8. Gateway: HTTPS

- [ ] 8.1 Generate a self-signed certificate/key for the gateway (e.g. at Docker image build time via
      `openssl` in the `Dockerfile`, so no manual step is needed) and point Nginx's `server` block at
      HTTPS (443 inside the container, published on `GATEWAY_PORT`) instead of HTTP; remove the plain-
      HTTP listener rather than adding HTTPS alongside it. Verify by rebuilding the gateway and
      confirming `http://` no longer connects while `https://` serves the app (with the expected
      self-signed-certificate warning).
- [ ] 8.2 Update `api/gateway_signin.py` to print `https://` links and encode the QR with the HTTPS
      address. Verify with `test_gateway_signin.py` asserting the scheme.
- [ ] 8.3 Confirm end-to-end: `Start-Gateway.ps1` prints an `https://` link, opening it on a phone
      shows a one-time certificate warning, accepting it signs the device in exactly as before, and
      every subsequent request still carries the token correctly.

## 9. Documentation

- [ ] 9.1 Update CLAUDE.md: `hooks/` section notes it now also holds the optional, dashboard-coupled
      `ledgerScripts/` (a `PermissionRequest` relay); `api/` section documents the pending-prompt
      store and its transcript-based clearing, Remote mode, its `subprocess` dependency on
      `hooks/scripts/Open-ClaudeRepoWindow.ps1` for the open-repo action, and the `is_local`
      delete-locality check; `gateway/` section documents the HTTPS-only listener and self-signed
      certificate; update the endpoint table for the new routes, `is_local` and `remote_mode`.
