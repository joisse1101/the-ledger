## Why

Setup is spread across `Start-Ledger.ps1`, `widget\Install-WidgetShortcut.ps1`,
`hooks\Install-ClaudeHooks.ps1` and `hooks\ledgerScripts\Install-HistoryBackupTask.ps1`, and none of
them tests the whole flow from a clean machine. Failures are silent: the widget shortcut stopped
working because `api\.venv` and `widget\node_modules` were left as empty folders, and
`Start-Widget.ps1` only checks that the folder exists. Fixed ports also make a start fail when
something else already holds one. Issue #54 asks for one wizard-style entry point.

## What Changes

- `Start-Ledger.ps1` becomes the one-stop start: it checks prerequisites, repairs missing or stale
  dependencies, resolves ports, starts the backend, frontend and desktop widget, then verifies each
  one answers and exits non-zero if any does not. `-NoWidget` skips the widget.
- Dependencies are checked by their real artifacts (the venv interpreter and requirements, `npm ci`
  for `web\` and `widget\`, the Electron binary), not by folder existence. `Start-Widget.ps1` uses
  the same check, so the hidden shortcut path repairs itself.
- Python and Node are required prerequisites, and Docker is required only with `-Remote`. When one
  is missing the script prints its official download page and stops.
- Ports are sticky and chosen from 8501-8599. Precedence: explicit parameter, `.env`, the saved
  choice, then a scan for a free port, which is saved. A saved port that is busy is reused when it is
  this app's backend and re-picked otherwise.
- When the chosen backend port differs from the one baked into an installed relay hook,
  `Start-Ledger.ps1` offers to reinstall the hook (asks with a console, reinstalls and says so
  without one or with `-Yes`).
- `Stop-Ledger.ps1` also closes the widget when `Start-Ledger.ps1` launched it, and leaves a widget
  that was already running alone.
- New `Install-Ledger.ps1` wizard, run once: offers the widget shortcut (and pre-warms the widget's
  dependencies), the toast hooks, the relay hook and the history backup task, saying for each what it
  does, what it changes on the machine and what declining means. It offers to reinstall an installed
  relay hook. Re-running changes nothing that is already current.
- The existing install and uninstall scripts stay as non-interactive helpers the wizard calls.
- `Start-Ledger.ps1`'s `-InstallBackupTask` is removed so the backup task has one install route.
  **BREAKING** for anyone using that flag; `Stop-Ledger.ps1 -UninstallBackupTask` is unaffected.
- New top-level `scripts/` folder holds the shared helper (port resolution, `.env` parsing,
  dependency checks) dot-sourced by the start and install scripts. **BREAKING** for the "exactly five
  top-level folders" rule in `CLAUDE.md` and `wiki/Repository-Layout.md`.
- Default frontend and gateway ports move from 4173 and 8080 into the 85xx range.

## Capabilities

### New Capabilities
- `app-startup`: the one-stop start and stop of the backend, frontend and widget, covering
  prerequisite and dependency checks, sticky port selection, startup order, verification and the
  stale relay-hook offer.
- `installer`: the one-time wizard that offers the widget shortcut, toast hooks, relay hook and
  history backup task, and the single install route for each.

### Modified Capabilities
- `desktop-widget`: the one-click shortcut start now repairs missing or stale widget dependencies
  and resolves ports the same way as the main start, instead of only checking the folder exists.

## Impact

- Scripts: `Start-Ledger.ps1`, `Stop-Ledger.ps1`, `widget\Start-Widget.ps1`,
  `hooks\Install-ClaudeHooks.ps1` (port resolution), new `Install-Ledger.ps1`, new `scripts\`.
- Port defaults: `api\app\core\config.py`, `widget\src\main\config.ts`,
  `api\app\infra\remote_system.py`, `gateway\Start-Gateway.ps1`, `gateway\docker-compose.yml`,
  `.env.example`. About 45 test fixtures use the old numbers as sample data and mostly need no change.
- New gitignored saved-ports file at the repo root.
- Docs: `README.md`, `CLAUDE.md` (layout and commands), `wiki/Setup-And-Run.md`, `wiki/Widget.md`,
  `wiki/Hooks.md`, `wiki/Gateway.md`, `wiki/Repository-Layout.md`; `check_docs.py` if it assumes
  the folder list.
