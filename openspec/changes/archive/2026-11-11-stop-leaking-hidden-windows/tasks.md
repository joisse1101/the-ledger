# Tasks

## 1. Chime child opens no window

- [x] 1.1 In `hooks/chimeScripts/Play-ClaudeChime.ps1`, start the sound child with `ProcessStartInfo` (`CreateNoWindow` on, `UseShellExecute` off) and put the title and `Ledger: Playing chimes...` line at the start of the child's command. Verify the existing chime tests in `api/tests/test_chime_hook.py` still pass.
- [x] 1.2 Add tests in `api/tests/test_chime_hook.py` using a fake `-PlayerPath`: the child's arguments contain `Ledger: Playing chimes...`, the child is started with no window, and the hook itself prints nothing and exits 0. Verify they fail on the old code and pass on the new.
- [x] 1.3 Update the chime section of `wiki/Services/Hooks.md` and the chime rule in `hooks/CLAUDE.md` (the child announces itself, the hook prints nothing). Verify `python scripts/check_docs.py` passes.

## 2. Open-repo and widget launch

- [x] 2.1 Move the no-window flag into one shared definition under `api/app/infra/`, point `repo_cli.py`, `remote_system.py` and `session_service.open_repo` at it, and pass it to the open-repo call. Verify `cd api; pytest` passes, including `test_layers.py`.
- [x] 2.2 Add a test in `api/tests/test_api_data.py` (next to the existing open-repo command check) that the open-repo call carries the no-window flag. Verify it fails without the flag.
- [x] 2.3 In `hooks/scripts/Open-ClaudeRepoWindow.ps1` and `widget/Start-Widget.ps1`, set the window title and print `Ledger: Opening repo in VS Code...` and `Ledger: Starting widget...`. Verify `widget/tests/Test-StartWidget.ps1` and the open-repo tests pass, and that each script still exits with its old exit code.
- [x] 2.4 Give the two `Start-Process powershell` commands in `Start-Ledger.ps1` the titles `Ledger: backend` and `Ledger: frontend`. Verify `.\Start-Ledger.ps1 -Help` still prints and the script parses.

## 3. Backup task has no console and logs its runs

- [x] 3.1 In `api/backup_history.py`, append `Ledger: Backing up history...`, then a success or failure line, to a log file beside `history.db`, keeping the existing print and never letting a logging failure fail the backup. Verify with a test using the `isolated_db` fixture that a success and a failure each leave the expected lines.
- [x] 3.2 In `hooks/ledgerScripts/Install-HistoryBackupTask.ps1`, register the task with `pythonw.exe` from the same `.venv\Scripts` folder, falling back to `python.exe` with a printed warning when it is missing. Verify with `api/tests/test_install_ledger.py` or a new test that the action's executable is `pythonw.exe` and that the fallback warns.
- [x] 3.3 Document the log file and the `pythonw.exe` task in `wiki/Services/Hooks.md`, and note that existing machines need the installer re-run. Verify `python scripts/check_docs.py` passes.

## 4. Tripwire for future leaks

- [x] 4.1 Add a test that scans `hooks/`, `widget/`, `api/app` and the root scripts for `Start-Process`, `subprocess` and `ProcessStartInfo` starts without a no-window marker, with an explicit allow-list for the two visible `Start-Ledger.ps1` windows. Verify it passes on the fixed code and fails when an unguarded start is added to a scratch copy.
- [x] 4.2 Document the rule and the allow-list in `hooks/CLAUDE.md` and `wiki/Contributing/Testing.md`. Verify `python scripts/check_docs.py` passes.

## 5. Final checks

- [x] 5.1 Run `cd api; pytest`, `cd api; pytest ../scripts/tests`, `cd web; npm test`, `cd web; npm run build` and `cd widget; npm test; npm run build`. Verify all pass.
- [x] 5.2 With a fake player, run the chime hook by hand with the AFK switch on and confirm no window opens and the hook prints nothing. Verify by watching for a `WindowsTerminal.exe -Embedding` process, which should not appear.

## Workflow follow-up

- Re-run `.\Install-Ledger.ps1` and accept the backup task to switch the existing scheduled task to `pythonw.exe` (owner: the user, after merge).
- Archive the change after review and update the affected wiki pages first.
