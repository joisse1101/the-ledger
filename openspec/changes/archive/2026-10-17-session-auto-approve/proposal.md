## Why

Approving every routine permission dialog by hand keeps a user tied to the terminal even when they
already trust what a session is doing. Prompts can already be answered from the dashboard, but only
one at a time and only by a person. A per-session auto-approve switch lets the user hand the plain
yes/no dialogs of one session to the app, while questions and plan approvals still wait for them.

## What Changes

- The backend keeps a per-session **auto-approve** flag (in memory, off after a backend restart,
  cleared when the session leaves the live list, expires after 8 hours like Remote mode).
- When a plain permission prompt registers for a flagged session, the backend answers it `allow` at
  once. Switching the flag on also approves prompts already pending for that session. Anything that
  is not a plain permission prompt (`AskUserQuestion`, `ExitPlanMode`) always waits for a human, and
  so does a shell command that matches a dangerous pattern (`sudo`, `rm -rf`, forced git pushes, ...).
- Only a request from the machine running the app can switch it; other devices see its state only.
- The backend remembers `relay_hook_seen`: true once any prompt has registered since the backend
  started. It is reported in `/api/meta`. Until it is true the switch is shown nowhere, since without
  the relay hook auto-approve could never act.
- `/api/live` rows gain `auto_approve`, and the last auto-approved prompt (tool name and time).
- Ledger web: a switch beside the session title in the Live session panel, an "Auto-approve" column
  in the Live sessions list only, and a "last auto-approved" line in the control view.
- Widget: a button at the right end of each row, nested in the clickable row, that does not open the
  repo window when pressed. This relaxes the widget rule that it never offers to approve prompts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `remote-session-control`: adds the auto-approve requirement (what is approved, when it stops,
  who may switch it, when the switch is shown).
- `desktop-widget`: "Rows flag a waiting prompt" no longer forbids all approval controls; adds a
  requirement for the per-row auto-approve button.
- `web-dashboard`: adds the Live panel switch and the Live list column.

## Impact

- `api/app/domain/pending_decisions.py` (flag store, `relay_hook_seen`, auto-answer in
  `request_decision`), `api/app/services/` (a toggle service, `prompt_service`), a new route under
  `api/app/routers/` (registered in `app/main.py`), `routers/meta.py` (via a `prompt_service`
  function), `api/app/schemas/`, `live_snapshot` rows via `prompt_service.live_with_prompts`.
- `web/src/api/types.ts` and `queries.ts`, `LiveSessionPanel.tsx`, `LiveControl.tsx`, `LiveList.tsx`.
- `widget/src/shared/types.ts`, `main/api.ts`, `preload`, `renderer/view.ts`, `app.ts`, `style.css`.
- Wiki: Backend-Live-Sessions-And-Prompts, Backend-API-Routes, Frontend-Sessions, Widget.
- Safety: auto-approve lets a session run any tool that shows a plain permission dialog unattended
  (including Bash). That is the purpose; the visible on-state, the audit line, the 8-hour expiry and
  the local-only switch are the guard rails.
- No change to the relay hook script or its installer.
