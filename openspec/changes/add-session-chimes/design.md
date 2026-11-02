# Design

## Context

- See `proposal.md` for the motivation and the `specs/` folder for the required behavior.
- Claude Code runs a `Notification` hook when a session needs input and a `Stop` hook when it finishes. The existing toast uses both (`hooks/scripts/Send-ClaudeToast.ps1`).
- Each hook is a fresh PowerShell process that gets a JSON payload on stdin. It keeps no memory between runs and cannot see other sessions.
- The installer for the relay hook (`-IncludeSessionControl`) is the pattern to copy: a switch on `Install-ClaudeHooks.ps1` and `Uninstall-ClaudeHooks.ps1` that adds or removes one entry in `settings.json` and a folder of scripts.
- The widget already reads one setting (`widget.max_projects`) from `GET /api/settings` over loopback and falls back to a default (`widget/src/main/api.ts`). The backend stores it in the settings file through `api/app/repositories/settings_store.py`, validated in `api/app/core/widget_settings.py`. The AFK duration follows the same path.
- The widget today writes only through the backend (Remote mode, auto-approve). The AFK switch is its first local file write.
- `wiki/Alert-Tiering-Ideas.md` records what is parked and why.

## Goals / Non-Goals

**Goals:**
- Work on any machine that has the hooks installed, with no widget, backend or BurntToast.
- Keep the sound logic in one small script that is easy to move into the widget later.
- Fail toward making the sound: a missed alert is worse than an extra one.
- Reuse the existing settings path for the AFK duration instead of adding storage.

**Non-Goals:**
- A delayed reminder when a session sits unanswered, away detection from session activity, skipping quick runs, escalation, tray or taskbar signals, speech, or other devices. All are parked in `wiki/Alert-Tiering-Ideas.md`.
- Making the 5-minute idle threshold or the 5-second merge window configurable.
- Telling terminals apart. The sound no longer depends on which window or repo is focused.

## Decisions

### One script, two kinds, installed in its own folder
- `hooks/chimeScripts/Play-ClaudeChime.ps1 -Kind done|needs-input` is registered on `Stop` (done) and `Notification` (needs-input) with an empty matcher, like the toast.
- It is installed to `%USERPROFILE%\.claude\hooks\chimeScripts\`.
- **Why a separate folder:** `Uninstall-ClaudeHooks.ps1` deletes every file listed in `hooks/scripts/` when the toasts are removed. A chime script placed there would vanish while its hook entries stayed. A separate folder mirrors `ledgerScripts/` and keeps the two installs independent.
- **Alternative:** extend `Send-ClaudeToast.ps1` to also play a sound. Rejected because the user must be able to have sounds without toasts, and the toast needs BurntToast.

### Install switch mirrors the relay hook
- `Install-ClaudeHooks.ps1 -IncludeChimes` adds the chime entries and copies the script. `-SkipToastHooks` already means "leave the toasts alone", so chimes-only is `-IncludeChimes -SkipToastHooks`.
- `Uninstall-ClaudeHooks.ps1 -IncludeChimes` removes just the chime entries and the folder, including the state files.
- Entries are matched by the script name `Play-ClaudeChime.ps1`, so a reinstall updates the path and never duplicates, and the user's own hooks are untouched.
- `Install-Ledger.ps1` gets a `-ChimeHooks ask|yes|no` choice, shown before the toast choice with the up-front explanation the installer spec requires.

### "Away" is idle time from Windows, or the AFK flag
- The script reads idle time with the Windows `GetLastInputInfo` call (in `user32.dll`) through `Add-Type`. Idle seconds is the current tick count minus the last-input tick count, both as unsigned 32-bit numbers so the 49-day wrap is harmless.
- The user is away when idle seconds is at least 300, or the AFK flag is valid. If the idle time cannot be read, the user counts as away, so the sound plays.
- The away check runs first and is cheap. Only an alert that passes it reaches the merge step, so a present user leaves no state behind.
- **Why not focus:** the first draft skipped the sound only when the repo's VS Code window was focused. The user wants silence whenever they are at the PC, so idle time replaces it, and the fragile window-title match is gone.
- **Alternative:** Electron's `powerMonitor.getSystemIdleTime()` in the widget. Rejected because it would stop the sounds working with the widget closed.
- **Limit:** reading or watching a video without touching the keyboard or mouse for 5 minutes counts as away. The user can accept that or ignore it.

### The AFK flag is a file holding its own expiry
- The file is `afk.flag` in `%USERPROFILE%\.claude\hooks\chimeScripts\state\`, the same folder as the merge state. It holds one UTC time: when the switch ends.
- The widget writes it when the switch is turned on (now plus the AFK duration) and deletes it when turned off. The hook treats a missing, unreadable or past-due file as no flag, so a crash or a widget that never ran again cannot leave AFK stuck on.
- Putting the expiry in the file means the hook needs neither the backend nor the setting. The hook never writes the flag.
- **Alternative:** the widget keeps the state and the hook asks the backend. Rejected because it needs the backend running and adds a network call to every alert.
- **Alternative:** a Windows registry value. Rejected as harder to inspect and reset than a file.

### The AFK duration is a setting the widget reads
- A new value `widget.afk_minutes` joins `widget.max_projects` in `GET` and `PUT /api/settings`: a whole number from 1 to 240, 30 when never set, validated beside `validate_max_projects`, stored in the same settings file.
- The widget reads it at the moment it turns AFK on, falling back to the last value it read, or 30 if it never read one. A later change applies to the next switch-on and never changes a flag already written.
- The Settings page's "Desktop widget" section gets one more number field, built like the existing one.
- The `dashboard-settings` spec's line that the widget "reads only" the projects setting is updated to name both.
- **Alternative:** a fixed 30 minutes. Rejected at the user's request.
- **Alternative:** the hook reads the setting. Rejected because the backend may be down and the hook must stay independent.

### The widget owns the flag's file I/O, behind the existing bridge
- A small pure module in the widget's main process reads the flag (off, or on with minutes left), writes it, clears it, and checks whether `Play-ClaudeChime.ps1` is installed. Each takes the folder as an argument so tests use throwaway folders.
- The main process reads the flag on each poll, beside `/api/live`, and pushes it to the renderer with the rest of the state. The button works when the backend is down because the flag needs no request.
- The renderer asks to switch it through a new channel on the preload bridge, exactly like `setAutoApprove`. The channel name goes in `widget/src/shared/ipc.ts`, and the existing test keeps the sandboxed preload's copy in step.
- The button is shown only when the chime script exists in the install folder, mirroring how the auto-approve button depends on the relay hook.

### Merging with a small state file under a named mutex
- The merge state is one file per kind in the same state folder, holding the time that kind last played.
- A run takes a named system mutex, reads the files, decides, writes the new time if it will play, and releases the mutex. The mutex stops two hooks firing together from both playing.
- The rule follows the spec: `done` skips if either file is newer than 5 seconds; `needs-input` skips only if its own file is.
- The files hold only timestamps, with no session data.
- **Alternative:** let the widget merge by watching state changes. Rejected for now: it needs the widget running and cannot see the `needs-input` event without the relay hook.

### Play detached, using the user's Windows sounds
- The script decides, then starts a hidden child PowerShell that plays the sound and exits, so the hook returns at once.
- `done` uses the Windows system sound `Asterisk` and `needs-input` uses `Hand`, through `System.Media.SystemSounds`. This adds no audio files, follows the user's sound scheme, and is silent if they turned system sounds off.
- **Alternative:** play `.wav` files from `C:\Windows\Media`, which waits until the sound ends but depends on file names that differ between Windows versions.
- **Alternative:** ship our own `.wav` files. Rejected as unneeded for a first version.

### Never speak to Claude Code
- The hook prints nothing and exits 0 on every path, including errors, as the relay hook does. A top-level `try/catch` swallows everything.
- A `-DryRun` switch exists only for tests. It prints the decision (`play`, `skip-present` or `skip-merged`) instead of playing, and is never part of an installed hook command.
- Two more test-only parameters, `-IdleSeconds` and `-StateDir`, replace the real idle clock and the real state folder. The flag is tested by writing `afk.flag` into the throwaway `-StateDir`.

## Risks / Trade-offs

- **Sound plays nothing** (system sounds off, no audio device) → The script cannot tell; it is silent by design, and the wiki page says to check the Windows sound scheme.
- **Forgotten AFK switch** → It turns itself off after the AFK duration, 30 minutes by default, and the hook ignores an expired file even if the widget is closed.
- **Repeated "needs input" sounds** → Claude Code's `Notification` event also fires for an idle prompt after a wait, so a long-ignored prompt may chime again while the user is away. Accepted for now; escalation is parked.
- **Idle time unreadable** → The user counts as away and the sound plays. This is the safe failure and may be noisier.
- **Widget and hook disagree on the folder** → Both derive it from `%USERPROFILE%`. A test pins the path in one place for each side so they cannot drift unnoticed.
- **Two hooks race on the state files** → The named mutex covers it. If the mutex cannot be taken quickly, the script plays rather than skips.
- **Extra PowerShell startup on every event** → About a third of a second, the same cost as the toast hook, and it runs alongside the built-in notification.
- **Behavior verified on one Claude Code version** → The `Notification` and `Stop` hooks are the same ones the toast already uses; re-check after a Claude Code upgrade, as for the relay hook.
- **Wider change** → Hooks, widget, backend and frontend all change. The tasks keep each layer in its own group so each can be reviewed and committed alone.

## Migration Plan

- No data to migrate. The chime hooks are off until the user accepts them in the installer or runs `Install-ClaudeHooks.ps1 -IncludeChimes`. The new setting defaults to 30 and needs no existing file to change.
- Roll back with `Uninstall-ClaudeHooks.ps1 -IncludeChimes`, which removes the entries and the folder, including the state files and any AFK flag.

## Open Questions

- Whether `Asterisk` and `Exclamation` sound right together. This is judged by ear during implementation and can change without affecting the specs.
- Whether the fixed 5-minute idle threshold and 5-second merge window feel right in daily use. The specs fix them, so changing either later means a spec change, but it does not change the approach.
