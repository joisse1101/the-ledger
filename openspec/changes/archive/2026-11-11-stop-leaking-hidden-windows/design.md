# Design

## Context

See proposal.md for why. Today the chime script starts its sound child with
`Start-Process -WindowStyle Hidden` (`hooks/chimeScripts/Play-ClaudeChime.ps1:146`). Windows 11
hands a new console to the default terminal, and Windows Terminal ignores the hidden request.

The other places that start a process fall into three groups:

- **Already safe:** the two `.vbs` launchers run `powershell.exe` through `wscript` with window style 0, and every `api/app/infra/` caller sets `CREATE_NO_WINDOW`.
- **Leaking or likely to leak:** `session_service.open_repo` (no creation flag) and the scheduled backup task (runs `python.exe`, a console program, as an interactive user).
- **Visible on purpose:** the two `-NoExit` windows `Start-Ledger.ps1` opens for the backend and frontend logs.

The chime hook must print nothing to Claude Code on every path (`hooks/CLAUDE.md`, `session-chimes`
spec). Its tests never play a sound; `-PlayerPath` swaps the program that plays it.

## Goals / Non-Goals

**Goals:**
- No background process opens a window, whatever the default terminal is.
- A window that still appears says which part of the Ledger opened it.
- A new leaky process start fails the test run.

**Non-Goals:**
- Changing the default terminal or any Windows setting.
- Touching the toast and relay hooks, which start no second process.
- Hiding the intentional backend and frontend windows.
- Changing when chimes play or how alerts merge.

## Decisions

### Chime child: ProcessStartInfo with no console
The chime script builds a `System.Diagnostics.ProcessStartInfo` with `CreateNoWindow = $true` and
`UseShellExecute = $false`, then calls `[Process]::Start`. The child has no console, so there is nothing
for Windows Terminal to take over.

Alternatives considered: `wscript` plus a `.vbs` launcher, as the other scripts do, works but adds a
file and a second host for a five-line change. Changing the Windows default terminal affects every
console program on the machine.

### The message lives in the child's command, not the parent
The parent keeps the print-nothing contract. The child's command text sets
`$Host.UI.RawUI.WindowTitle = 'Ledger: Playing chimes...'` and runs `Write-Host` with the same text
before it plays the sound. Both are inside the existing `try`, so a failure to set the title cannot stop
the sound. With no console the message is never seen; it exists only for the slip-through case.

`-PlayerPath` stays test-only. Tests assert the child's command string contains the message and run
with a fake player, so no sound plays.

### Open-repo: add the creation flag and name the script
`session_service.open_repo` passes `creationflags=NO_WINDOW`. The constant already exists in two infra
modules, and `session_service` sits above `infra` in the layering, so importing it from there is
allowed. Duplicating it in the service would repeat it a third time, so the task reuses one shared
definition. `Open-ClaudeRepoWindow.ps1` sets its title to `Ledger: Opening repo in VS Code...` and prints
the same line. Output goes to the backend, which does not read it, so nothing else changes.

### Widget launch and start windows: titles only
`Start-Widget.ps1` sets its title to `Ledger: Starting widget...` and prints it. `Start-Ledger.ps1` gives
its two `Start-Process powershell` commands a `$Host.UI.RawUI.WindowTitle` line, `Ledger: backend` and
`Ledger: frontend`. These windows stay visible.

### Backup task: pythonw plus a log file
The installer registers the task with `pythonw.exe` from the same `.venv\Scripts` folder. `pythonw.exe`
has no console, so a printed message would go nowhere. `backup_history.py` therefore appends its
`Ledger: Backing up history...` line, then a success or failure line, to a log file beside
`history.db`. The existing `print` stays for the interactive run. The log is appended, never rewritten,
and a failure to write it must not fail the backup.

Existing machines keep the old `python.exe` task until the user re-runs `Install-Ledger.ps1`, which
already updates the task in place (`Set-ScheduledTask`).

### Guard test: scan for unguarded process starts
One test reads `.ps1`, `.py` and `.vbs` files under `hooks/`, `widget/`, `api/app`, and the root scripts,
and fails when it finds `Start-Process`, `subprocess.run/Popen` or `ProcessStartInfo` without a
no-window marker on the same call. A short allow-list names the deliberate exceptions: the two
`Start-Ledger.ps1` windows and test files. The test is a text scan, so it is a tripwire rather than proof;
it exists so a future contributor is stopped and has to state why a window is acceptable.

## Risks / Trade-offs

- [The text scan misses a start built dynamically, or flags a harmless one] → Keep the allow-list explicit, and document the rule in `hooks/CLAUDE.md` so reviewers apply it too.
- [`pythonw.exe` is missing from a venv] → The installer checks for it and falls back to `python.exe` with a printed warning, so the task is never left unable to run.
- [A silent backup failure, now that no console shows it] → The log file records each run, and the existing "trigger it once now" step in the installer output still prints to a console.
- [The 2 pm console flash was never observed] → Treated as likely; the change is harmless if it was not happening.

## Migration Plan

Ship the code. The chime, open-repo and widget fixes take effect on the next run. For the backup
task, re-run `.\Install-Ledger.ps1` and accept the backup task to update it to `pythonw.exe`. Rollback
is reverting the commit and re-running the installer.
