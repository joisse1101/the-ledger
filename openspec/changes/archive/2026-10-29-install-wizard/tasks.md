## 1. Shared helper and layout

- [x] 1.1 Create `scripts\` with the shared helper (`.env` parsing, port resolution, prerequisite check, dependency check) and update `CLAUDE.md` Layout, `wiki\Repository-Layout.md` and any `check_docs.py` folder assumption; verify `cd api; python check_docs.py` passes
- [x] 1.2 Add tests for the helper's pure logic (port precedence, free-port scan, stamp comparison) and verify they pass and touch no real user state

## 2. Sticky ports

- [x] 2.1 Implement the saved-ports file (gitignored at the repo root) and the 8501-8599 scan with the reuse-if-our-backend rule; verify the first-run, later-run, taken-by-other and held-by-this-app scenarios in tests
- [x] 2.2 Move the default frontend and gateway ports in `api\app\core\config.py`, `widget\src\main\config.ts`, `api\app\infra\remote_system.py`, `gateway\Start-Gateway.ps1`, `gateway\docker-compose.yml` and `.env.example`; verify `cd api; pytest` and `cd widget; npm test` pass

## 3. Dependency repair and prerequisites

- [x] 3.1 Implement the prerequisite check (Python, Node, Docker only with `-Remote`) printing official download pages and exiting non-zero; verify with a test that simulates a missing tool
- [x] 3.2 Implement artifact-and-stamp dependency repair for the venv, `web\`, `widget\` and the Electron binary; verify the empty-folder, missing-Electron, everything-current and repair-fails scenarios
- [x] 3.3 Make `widget\Start-Widget.ps1` use the shared repair and port helpers instead of its own checks; verify `powershell -File widget\tests\Test-StartWidget.ps1` passes including an empty `node_modules` case

## 4. One-stop start and stop

- [x] 4.1 Rework `Start-Ledger.ps1` to run prerequisites, repair, ports, then start the backend, frontend and widget in order, with `-NoWidget`; verify the widget starts only after `/api/meta` answers
- [x] 4.2 Add the post-start verification summary and failure exit code; verify a deliberately failing frontend yields a non-zero exit
- [x] 4.3 Record the widget PID only when Start launched it and make `Stop-Ledger.ps1` close it; verify the already-running-widget case leaves it alone
- [x] 4.4 Remove `-InstallBackupTask` from `Start-Ledger.ps1` and its help text; verify no script, doc or spec still references the flag

## 5. Relay hook port staleness

- [x] 5.1 Detect an installed relay hook's baked port and, in `Start-Ledger.ps1`, ask (console) or reinstall with a notice (no console or `-Yes`); verify the three scenarios against a temporary settings file, not the real one
- [x] 5.2 Make `hooks\Install-ClaudeHooks.ps1` resolve its port through the shared helper; verify `api\tests\test_hook_install.py` passes

## 6. Installer

- [x] 6.1 Add non-interactive switches to the install helpers that lack one; verify each runs without prompting
- [x] 6.2 Create `Install-Ledger.ps1` offering the shortcut (with logon autostart choice), toast hooks, relay hook and backup task, each with what it does, what it changes and what declining means; verify declining installs nothing
- [x] 6.3 Have the installer pre-warm widget dependencies on accepting the shortcut and offer a reinstall when the relay hook is installed; verify a clean machine ends with a working shortcut
- [x] 6.4 Verify a second installer run duplicates no shortcut, hook entry or scheduled task

## 7. Docs and specs

- [x] 7.1 Update `README.md`, `wiki\Setup-And-Run.md`, `wiki\Widget.md`, `wiki\Hooks.md`, `wiki\Gateway.md` and the `CLAUDE.md` command list so the installer is the setup step and start and stop the run step; verify `cd api; python check_docs.py` passes
- [x] 7.2 Run the full suites and verify they pass: `cd api; pytest`, `cd web; npm test`, `cd web; npm run build`, `cd widget; npm test; npm run build`
