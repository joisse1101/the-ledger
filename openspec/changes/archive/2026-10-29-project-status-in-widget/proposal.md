## Why

The Projects page shows each project's repo host and open issue and pull request counts, but only
in the browser. The desktop widget is the always-visible surface, and the user wants those counts
there without opening the dashboard.

## What Changes

- Hovering the widget's Ledger button shows a tooltip window below the widget (placed like the
  Remote tooltip) listing GitHub projects with name, source, open issues and open pull requests.
- The list is limited to the top N projects by open issues plus pull requests, with a "+N more"
  line. N is a setting, default 5, changed on the dashboard's Settings page.
- The Remote status and sign-in code tooltip moves from the Ledger button to the Remote button. It
  keeps its behavior (messages while starting or failed, QR while ready, auto-show on ready); only
  its trigger changes.
- The widget fetches project repo info and the setting at startup, every 60 seconds, and on each
  hover, so a hover shows the last known rows at once and updates in place when fresher data lands.
- The Settings page gains a "Desktop widget" section with the projects-shown number. The setting is
  saved on its own, without the history and snapshot reconciliation that saving worktree folders runs.
- **BREAKING** (behavior): hovering the Ledger button no longer shows Remote status or the QR code.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `desktop-widget`: the hover requirement moves to the Remote button, and a new requirement adds the
  Ledger button's projects tooltip.
- `dashboard-settings`: a new requirement adds the widget's projects-shown setting, and the
  "widget SHALL NOT offer settings" wording is clarified so the widget may read a setting but never
  show or change one.

## Impact

- `widget/src/main/` (`api.ts`, `remoteTooltip.ts`, `tooltipWindow.ts`, `index.ts`, a new projects
  tooltip controller), `widget/src/renderer/` (`app.ts`, `tooltipView.ts`), `widget/src/preload/`,
  `widget/src/shared/` (`ipc.ts`, `types.ts`), and widget tests.
- `api/`: `settings_store.py` (read-modify-write so one key never erases another), `settings_service.py`,
  `routers/settings.py`, `schemas/settings.py`, and tests. No change to `/api/projects/repos`.
- `web/`: `SettingsPage.tsx`, `api/types.ts`, `api/queries.ts`, and tests.
- Docs: `wiki/Widget.md`, `wiki/Backend-API-Routes.md`, `wiki/Frontend-Shell-And-Theme.md` or the
  Settings page's wiki page, as `check_docs.py` requires.
