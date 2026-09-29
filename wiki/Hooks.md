# Hooks

> Requirements live in `openspec/specs/toast-context-line/spec.md`, `openspec/specs/remote-session-control/spec.md`. This page describes how the code meets them, not what it must do.

`hooks/scripts/` is a standalone utility, unrelated to the dashboard: Windows toast notifications for
Claude Code's `Notification`/`Stop` hook events, with `Install-ClaudeHooks.ps1`/
`Uninstall-ClaudeHooks.ps1` to set them up on a machine. See `hooks/README.md` for how it works and
full install/uninstall/test steps. (The dashboard's one reach into it: `api/` runs
`hooks/scripts/Open-ClaudeRepoWindow.ps1` for the open-repo action — see [API routes](Backend-API-Routes.md).)

`hooks/ledgerScripts/` is the exception: **optional, dashboard-coupled** scripts, kept apart from
`scripts/` precisely because they only make sense with this app — one Claude Code hook plus two
plain Task Scheduler scripts that are dashboard-coupled the same way but aren't hooks at all.
`Relay-PermissionRequest.ps1` is a `PermissionRequest` hook that forwards each prompt Claude Code is about to show (permission dialog
or `AskUserQuestion`) to `POST /api/sessions/{id}/decisions` on `127.0.0.1:<port>` (`-Port`, baked in
by the installer, else `$env:LEDGER_PORT`, else 8501) and waits, so the dashboard can answer it. It
must **print nothing at all** — empty stdout, exit 0 — whenever it has no answer (backend down, no
answer in time, any error): any output is a decision, and silence leaves the terminal dialog as the
only way to answer, exactly as if the hook weren't installed. The hook is machine-wide, so it fires
for every session, not just ones the dashboard shows. It's installed separately from the toast
hooks: `Install-ClaudeHooks.ps1 -IncludeSessionControl` (add `-SkipToastHooks` for the relay alone)
copies it to `%USERPROFILE%\.claude\hooks\ledgerScripts\`, merges the `PermissionRequest` entry
(empty matcher, `timeout` 1810s — kept above the script's own 1805s wait) into `settings.json`, and
removes the legacy `PreToolUse` relay entry an earlier version of this feature installed;
`Uninstall-ClaudeHooks.ps1 -IncludeSessionControl` removes just the relay entries. Behavior was
verified against Claude Code 2.1.281 (the hook runs alongside the dialog, a late hook result is
discarded, `updatedInput.answers` answers an `AskUserQuestion`) — re-check after a Claude Code
upgrade. See `hooks/README.md` section 6.

`Install-HistoryBackupTask.ps1`/`Uninstall-HistoryBackupTask.ps1`, alongside the relay hook in the
same folder, register/remove the Windows Scheduled Task that runs `api/backup_history.py` daily
(see [Setup and run](Setup-And-Run.md)) — unlike the relay hook, these aren't Claude Code hooks at all (nothing
copies them anywhere or touches `settings.json`); they're run directly from this checkout, either by
hand or via the root `Start-Ledger.ps1 -InstallBackupTask`/`Stop-Ledger.ps1 -UninstallBackupTask`.
They live here rather than in `api/` because, like the relay hook, they're PowerShell tooling
specific to this app rather than part of the Python backend itself.
