## 1. Backend policy and state

- [x] 1.1 Add `api/app/domain/auto_approve_policy.py` with `is_auto_approvable(tool_name, tool_input)`, `DANGEROUS_COMMAND_PATTERNS` and the moved `QUESTION_TOOL`; point `decision_service` at it. Verify `api/tests/domain/test_auto_approve_policy.py` passes: questions and `ExitPlanMode` refused, ordinary `Edit`/`npm test` allowed, each pattern family (`sudo`, `rm -rf`, `Remove-Item -Recurse`, forced push, `curl | sh`, chained `a && sudo b`) refused, missing or non-string `command` on `Bash`/`PowerShell` refused
- [x] 1.2 Add the per-session flag, `_last_auto_approved`, `_relay_hook_seen` and their methods to `PendingDecisions` (`set_auto_approve`, `auto_approve_enabled` with lazy 8-hour expiry, `last_auto_approved`, `relay_hook_seen`, `prune_auto_approve`); `register()` sets `_relay_hook_seen`. Verify extended `api/tests/domain/test_pending_decisions.py` covers default off, expiry with the injected clock, pruning, and that the flag is set by the first `register()`
- [x] 1.3 Make `request_decision()` auto-answer `allow` when the flag is on and the policy passes, record the last auto-approved prompt, and log it as a structured line without `tool_input`. Verify tests: plain prompt resolves immediately, question/plan/dangerous command stay pending, other sessions are unaffected, a toggle-versus-register race answers a prompt once

## 2. Backend service, routes and payloads

- [x] 2.1 Add `api/app/services/auto_approve_service.py` (`set_enabled(session_id, enabled)`: reject a session that is not live, set the flag, then answer the already-pending approvable prompts). Verify `api/tests/services/test_auto_approve_service.py` covers turning on with a pending prompt, off, and a non-live session raising the service error
- [x] 2.2 Add `POST /api/sessions/{id}/auto-approve` (`routers/auto_approve.py`, `{enabled}` body schema in `schemas/auto_approve.py`, router registered in `app/main.py`) that returns 403 when not `is_local`. Verify route tests in `test_api_data.py`: local succeeds, non-local with a valid token gets 403 and no state change, unknown session errors
- [x] 2.3 Add `auto_approve` and `last_auto_approved` to the rows from `prompt_service.live_with_prompts` (calling `prune_auto_approve` with the live ids) and `relay_hook_seen` to `/api/meta` (add `prompt_service.relay_hook_seen()`; the router cannot import `deps`). Verify `test_api_data.py`/`test_main.py` assertions for the new fields, including them visible to a non-local client
- [x] 2.4 Run `cd api; pytest` and confirm the whole suite passes

## 3. Ledger web

- [x] 3.1 Mirror the new fields in `web/src/api/types.ts` and add `useSetAutoApprove(sessionId)` to `web/src/api/queries.ts`, invalidating the live query. Verify a `queries.test.tsx` case posts to the route and refreshes the live list
- [x] 3.2 Show the switch beside the title in `LiveSessionPanel.tsx` (existing switch component), only when `meta.relay_hook_seen` and `meta.is_local`, a read-only "Auto-approve on" label for non-local devices, and the "last auto-approved" caption in `LiveControl.tsx`. Verify component tests for: hidden before the hook is seen, visible on the PC, read-only elsewhere, caption present only when set
- [x] 3.3 Make `LiveList.tsx` columns depend on `relay_hook_seen` and add the Auto-approve column (Live list only; check narrow-layout handling against the `responsive-layout` spec). Verify tests: column absent before the hook is seen, marks only rows with it on, All sessions list unchanged
- [x] 3.4 Run `cd web; npm test` and `npm run build` and confirm both pass (type errors fail the build)

## 4. Widget

- [x] 4.1 Extend `widget/src/shared/types.ts` and `widget/src/main/api.ts` (parse `relay_hook_seen` from meta, add `setAutoApprove`), plus the IPC channel and preload exposure. Verify `api.test.ts` and `ipc.test.ts` cover the request, an unexpected payload (treated as hook not seen) and a failed call
- [x] 4.2 Rework `renderer/view.ts` rows into a wrapper holding the open-repo button and a sibling auto-approve button at the right end (on/off look, hover text, hidden until the hook is seen), wired through `app.ts`, and style it in `style.css`. Verify `renderer.test.ts`: pressing it calls `setAutoApprove` and does not open the repo, state follows the next poll, no button before the hook is seen, and existing row tests are updated for the new markup
- [x] 4.3 Run `cd widget; npm test; npm run build` and confirm both pass

## 5. Docs and verification

- [x] 5.1 Update `wiki/Backend-Live-Sessions-And-Prompts.md`, `wiki/Backend-API-Routes.md`, `wiki/Frontend-Sessions.md` and `wiki/Widget.md` (route, fields, policy and the best-effort caveat, switch, column, button); verify `cd api; python check_docs.py` passes
- [x] 5.2 Start the stack with `.\Start-Ledger.ps1` and the widget, relay a real prompt, and check by hand: controls appear only after the first prompt, a plain tool is approved, a question, `ExitPlanMode` and a `sudo` command pause, and the Ledger and widget stay in step
