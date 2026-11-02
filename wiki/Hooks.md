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
by the installer from the shared port rules (parameter, root `.env`, saved port, first free port in
8501-8599), else `$env:LEDGER_PORT`, else 8501) and waits, so the dashboard can answer it. It
must **print nothing at all** — empty stdout, exit 0 — whenever it has no answer (backend down, no
answer in time, any error): any output is a decision, and silence leaves the terminal dialog as the
only way to answer, exactly as if the hook weren't installed. The hook is machine-wide, so it fires
for every session, not just ones the dashboard shows. `Install-Ledger.ps1` offers the toast hooks and
the relay hook as separate choices, each preceded by what it changes (it edits `settings.json`; the
toast hooks also register the `claudecode://` handler), and offers a reinstall instead when the relay
hook is already installed. It calls `Install-ClaudeHooks.ps1`, which installs the relay separately from
the toast hooks: `-IncludeSessionControl` (add `-SkipToastHooks` for the relay alone) copies it to `%USERPROFILE%\.claude\hooks\ledgerScripts\`, merges the `PermissionRequest` entry
(empty matcher, `timeout` 1810s — kept above the script's own 1805s wait) into `settings.json`, and
removes the legacy `PreToolUse` relay entry an earlier version of this feature installed;
`Uninstall-ClaudeHooks.ps1 -IncludeSessionControl` removes just the relay entries. Behavior was
verified against Claude Code 2.1.281 (the hook runs alongside the dialog, a late hook result is
discarded, `updatedInput.answers` answers an `AskUserQuestion`) — re-check after a Claude Code
upgrade. See `hooks/README.md` section 6. The port is baked into `settings.json`, so when the backend
moves to another port `Start-Ledger.ps1` notices the mismatch and offers to reinstall the hook (asks
with a console; reinstalls and says so without one, or with `-Yes`).

`hooks/chimeScripts/Play-ClaudeChime.ps1` is the **chime script**: a short Windows sound when a
session needs you, played only while you are away. Like the toast hooks it is machine-wide and has
nothing to do with the dashboard. `Install-ClaudeHooks.ps1 -IncludeChimes` copies it to
`%USERPROFILE%\.claude\hooks\chimeScripts\` and merges one `Stop` entry (`-Kind done`) and one
`Notification` entry (`-Kind needs-input`), both with an empty matcher, matched by script name so a
re-run updates the path and never duplicates. Add `-SkipToastHooks` for chimes alone: no toast script,
no BurntToast, no `claudecode://` handler. `Uninstall-ClaudeHooks.ps1 -IncludeChimes` removes just those
entries (toast and your own hooks stay) and the folder with its state files and any AFK flag. The folder
is separate from `scripts/` because the toast uninstall deletes every file listed there. See
`hooks/README.md` section 7.

- **Two kinds.** `-Kind done` (for the `Stop` event) plays Asterisk. `-Kind needs-input` (for the
  `Notification` event) plays Exclamation. Any other kind does nothing.
- **Away rule.** Away means no keyboard or mouse input for 300 seconds or more (`GetLastInputInfo`),
  or a valid `afk.flag` in the state folder (a UTC expiry time still in the future). If Windows will
  not report idle time, you count as away. A missing, garbled or past-due flag counts as no flag.
  A present user leaves no state behind.
- **Merge rule.** Alerts within 5 seconds make one sound. Each kind keeps a timestamp file in the
  state folder, guarded by a named mutex. `done` is skipped after any recent sound. `needs-input` is
  skipped only after a recent `needs-input`, so a finish never hides a request for input. If the
  mutex or the folder is unusable, the sound plays.
- **Silence contract.** The script prints nothing and exits 0 on every path, so it cannot disturb
  Claude Code. The sound plays from a hidden child PowerShell, so the hook returns at once.
- **Test-only parameters.** `-DryRun` prints `play`, `skip-present` or `skip-merged` instead of
  playing. `-IdleSeconds` replaces the idle clock (negative means unreadable). `-StateDir` replaces
  the state folder. `-PlayerPath` replaces the program that plays the sound. `api/tests/test_chime_hook.py`
  uses all four with throwaway folders, so no sound plays and the real state is never touched.
- **Unchecked by ear.** Tests cover the decisions, not the sound. That the two sounds differ and are
  audible is not yet checked; it needs a person listening on a real machine.

`Install-HistoryBackupTask.ps1`/`Uninstall-HistoryBackupTask.ps1`, alongside the relay hook in the
same folder, register/remove the Windows Scheduled Task that runs `api/backup_history.py` daily
(see [Setup and run](Setup-And-Run.md)) — unlike the relay hook, these aren't Claude Code hooks at all (nothing
copies them anywhere or touches `settings.json`); they're run directly from this checkout.
`Install-Ledger.ps1` is the install route (offered as the history backup task, and the root
`Start-Ledger.ps1` no longer installs it); `Stop-Ledger.ps1 -UninstallBackupTask` is the shortcut for
removing the task.
They live here rather than in `api/` because, like the relay hook, they're PowerShell tooling
specific to this app rather than part of the Python backend itself.
