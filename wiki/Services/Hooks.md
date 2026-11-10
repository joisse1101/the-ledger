# Hooks

This page explains the PowerShell scripts under `hooks/`: Windows toast notifications, the optional relay hook, the chime script and the history backup task scripts. Read it to learn what each script does and how it is installed.

> Requirements live in `openspec/specs/toast-context-line/spec.md`, `openspec/specs/remote-session-control/spec.md`. This page describes how the code meets them, not what it must do.

A hook is a command Claude Code runs when an event happens, such as a notification or a stop.

## Toast hooks

### What they are

`hooks/scripts/` is a standalone utility, unrelated to the dashboard. It shows Windows toast notifications for Claude Code's `Notification` and `Stop` hook events. `Install-ClaudeHooks.ps1` and `Uninstall-ClaudeHooks.ps1` set them up on a machine and remove them. See `hooks/README.md` for how it works and the full install, uninstall and test steps.

### The dashboard's reach into it

`api/` runs `hooks/scripts/Open-ClaudeRepoWindow.ps1` for the open-repo action. See [API routes](../Backend/API-Routes.md).

## Dashboard-coupled scripts

### What lives in `hooks/ledgerScripts/`

`hooks/ledgerScripts/` is the exception: optional scripts that are coupled to the dashboard. It is kept apart from `scripts/` because the scripts only make sense with this app.

It holds one Claude Code hook: `Relay-PermissionRequest.ps1`. It also holds two plain Task Scheduler scripts, which are dashboard-coupled the same way but are not hooks at all.

## Relay hook

The relay hook is defined in the [Glossary](../Glossary.md#relay-hook). Without it the dashboard cannot show or answer pending decisions.

### What it does

`Relay-PermissionRequest.ps1` is a `PermissionRequest` hook. It forwards each prompt Claude Code is about to show, a permission dialog or `AskUserQuestion`. It posts to `POST /api/sessions/{id}/decisions` on `127.0.0.1:<port>`. It then waits, so the dashboard can answer the prompt.

The hook is machine-wide, so it fires for every session, not just ones the dashboard shows.

### Which port it uses

The port is `-Port`, baked in by the installer from the shared port rules. Those rules are: parameter, root `.env`, saved port, first free port in 8501-8599. Otherwise it uses `$env:LEDGER_PORT`. Otherwise it uses 8501.

The port is baked into `settings.json`. When the backend moves to another port, `Start-Ledger.ps1` notices the mismatch and offers to reinstall the hook. It asks with a console. It reinstalls and says so without a console, or with `-Yes`.

### The silence rule

It must **print nothing at all** whenever it has no answer: empty stdout, exit 0. No answer means: backend down, no answer in time, or any error. Any output is a decision.

Silence leaves the terminal dialog as the only way to answer. That is exactly as if the hook were not installed.

### Installing it

`Install-Ledger.ps1` offers the toast hooks and the relay hook as separate choices. Each choice is preceded by what it changes. It edits `settings.json`. The toast hooks also register the `claudecode://` handler. It offers a reinstall instead when the relay hook is already installed.

`Install-Ledger.ps1` calls `Install-ClaudeHooks.ps1`, which installs the relay separately from the toast hooks. `-IncludeSessionControl` installs the relay. Add `-SkipToastHooks` for the relay alone.

The install does three things:

- It copies the script to `%USERPROFILE%\.claude\hooks\ledgerScripts\`.
- It merges the `PermissionRequest` entry into `settings.json`. That entry has an empty matcher and `timeout` 1810s, kept above the script's own 1805s wait.
- It removes the legacy `PreToolUse` relay entry an earlier version of this feature installed.

`Uninstall-ClaudeHooks.ps1 -IncludeSessionControl` removes just the relay entries.

### What was verified

Known: behavior was verified against Claude Code 2.1.281.

- The hook runs alongside the dialog.
- A late hook result is discarded.
- `updatedInput.answers` answers an `AskUserQuestion`.

To do: re-check this after a Claude Code upgrade. See `hooks/README.md` section 6.

## Chime script

### What it is

`hooks/chimeScripts/Play-ClaudeChime.ps1` is the **chime script**. It plays a short Windows sound when a session needs you, only while you are away. Like the toast hooks, it is machine-wide and has nothing to do with the dashboard.

### Installing it

`Install-ClaudeHooks.ps1 -IncludeChimes` copies it to `%USERPROFILE%\.claude\hooks\chimeScripts\`. It merges one `Stop` entry (`-Kind done`) and one `Notification` entry (`-Kind needs-input`). Both entries have an empty matcher. They are matched by script name, so a re-run updates the path and never duplicates.

Add `-SkipToastHooks` for chimes alone: no toast script, no BurntToast, no `claudecode://` handler.

`Uninstall-ClaudeHooks.ps1 -IncludeChimes` removes just those entries. Toast and your own hooks stay. It also removes the folder with its state files and any AFK flag. The folder is separate from `scripts/` because the toast uninstall deletes every file listed there. See `hooks/README.md` section 7.

### How it behaves

**Two kinds.** `-Kind done` (for the `Stop` event) plays Asterisk. `-Kind needs-input` (for the `Notification` event) plays Hand. Any other kind does nothing. Both sounds follow the Windows sound scheme. Some Windows 11 schemes map Asterisk and Exclamation to the same file, which is why needs-input uses Hand. If the two chimes sound alike, check Sound settings.

**Away rule.** Away means no keyboard or mouse input for 300 seconds or more (`GetLastInputInfo`). Away also means a valid `afk.flag` in the state folder: a UTC expiry time still in the future. If Windows will not report idle time, you count as away. A missing, garbled or past-due flag counts as no flag. A present user leaves no state behind.

**Merge rule.** Alerts within 5 seconds make one sound. Each kind keeps a timestamp file in the state folder, guarded by a named mutex. `done` is skipped after any recent sound. `needs-input` is skipped only after a recent `needs-input`, so a finish never hides a request for input. If the mutex or the folder is unusable, the sound plays.

**Silence contract.** The script prints nothing and exits 0 on every path, so it cannot disturb Claude Code. The sound plays from a child PowerShell started with no console (`CreateNoWindow`), so the hook returns at once and no window opens, even when Windows Terminal is the default terminal. A hidden window style is not enough there. The child sets its window title to `Ledger: Playing chimes...` and prints the same line, so a window that still slips through can be traced. The hook itself prints nothing.

### Test-only parameters

- `-DryRun` prints `play`, `skip-present` or `skip-merged` instead of playing.
- `-IdleSeconds` replaces the idle clock; negative means unreadable.
- `-StateDir` replaces the state folder.
- `-PlayerPath` replaces the program that plays the sound.

`api/tests/test_chime_hook.py` uses all four with throwaway folders. No sound plays and the real state is never touched.

### Unchecked by ear

Tests cover the decisions, not the sound. Unchecked: that the two sounds differ and are audible. A person must listen on a real machine to check this.

## History backup task scripts

`Install-HistoryBackupTask.ps1` and `Uninstall-HistoryBackupTask.ps1` register and remove the Windows Scheduled Task. The task runs `api/backup_history.py` daily. See [Setup and run](../Contributing/Setup-And-Run.md).

The task runs `pythonw.exe` (Python without a console) so no window flashes. Because nothing can be printed to a console, `backup_history.py` appends each run to `backup.log` beside `history.db`: a `Ledger: Backing up history...` line, then a success or failure line. A logging problem never fails the backup. If `pythonw.exe` is missing from the venv, the installer prints a warning and registers `python.exe`. A task registered earlier keeps `python.exe` until `Install-Ledger.ps1` is re-run and the backup task accepted. The installer's `-ScriptsDir` parameter is test-only.

They sit alongside the relay hook in the same folder. Unlike the relay hook, they are not Claude Code hooks at all. Nothing copies them anywhere or touches `settings.json`. They run directly from this checkout.

`Install-Ledger.ps1` is the install route; it offers the history backup task. The root `Start-Ledger.ps1` no longer installs it. `Stop-Ledger.ps1 -UninstallBackupTask` is the shortcut for removing the task.

They live here rather than in `api/` because they are PowerShell tooling specific to this app. They are not part of the Python backend itself.
