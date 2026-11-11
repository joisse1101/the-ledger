# Proposal

## Why

Every time a Claude Code session finishes or needs input, an empty terminal window flashes for about
1.5 seconds. The chime script starts a second `powershell.exe` with `Start-Process -WindowStyle Hidden`,
and on Windows 11 the default terminal (Windows Terminal) ignores the "hidden" request and opens a window.
The user cannot tell which script opened it.

Other places start processes the same way, so the same flash can happen elsewhere. The fix should cover
all of them and make any window that still slips through say where it came from.

## What Changes

- The chime script starts its sound child with `ProcessStartInfo` (`CreateNoWindow` on, `UseShellExecute` off), so the child has no console and Windows Terminal has nothing to show.
- The chime child sets its window title and prints `Ledger: Playing chimes...`. The parent script still prints nothing.
- The backend starts the open-repo script with `CREATE_NO_WINDOW`, as the other `api/app/infra/` callers already do.
- `Open-ClaudeRepoWindow.ps1` and `Start-Widget.ps1` set their window title and print a `Ledger: ...` line, so a window that slips through is identifiable.
- The daily history backup task runs `pythonw.exe` (no console) instead of `python.exe`, and `backup_history.py` writes a `Ledger: ...` line to a log file, since a console message would never be seen.
- The visible backend and frontend windows opened by `Start-Ledger.ps1` get titles (`Ledger: backend`, `Ledger: frontend`) so they are told apart from a stray window.
- A test scans `hooks/`, `widget/`, `api/` and the root scripts for process starts that lack a no-window guard, so a new leaky start fails the build.
- The Hooks wiki page, `hooks/CLAUDE.md` and the specs are updated to match.

## Capabilities

### New Capabilities
- `background-process-visibility`: processes the Ledger starts in the background show no window, and any that still show one name themselves as `Ledger: <what it is doing>`.

### Modified Capabilities
- `session-chimes`: the "failing sound never disturbs Claude Code" requirement gains the rule that the sound child opens no window and announces itself, while the hook itself still prints nothing.

## Impact

- **Code:** `hooks/chimeScripts/Play-ClaudeChime.ps1`, `hooks/scripts/Open-ClaudeRepoWindow.ps1`, `widget/Start-Widget.ps1`, `Start-Ledger.ps1`, `api/app/services/session_service.py`, `api/backup_history.py`, `hooks/ledgerScripts/Install-HistoryBackupTask.ps1`.
- **Tests:** the existing chime, widget, hook-install and open-repo tests, plus a new process-start scan test.
- **Docs:** `wiki/Services/Hooks.md`, `hooks/CLAUDE.md`.
- **Machine state:** the existing backup scheduled task keeps running `python.exe` until the user re-runs the installer, which updates the task in place.
- **Not affected:** the toast and relay hooks start no second process, and the `.vbs` launchers already hide their window.
- **Unchecked:** whether the backup task's `python.exe` console flashes today. The user's 2 pm run was not observed, so this is treated as likely.
