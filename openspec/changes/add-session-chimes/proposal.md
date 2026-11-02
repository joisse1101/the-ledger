# Proposal

## Why

A Claude Code session that finishes or waits for input is easy to miss when you have left your desk. The only alert today is the Windows toast, which fires for every event from every session, so it is loud and easy to learn to ignore. A short sound reaches you when you are away, and staying silent while you are at the PC keeps it from becoming another annoying alert.

## What Changes

- Add two short sounds played by Claude Code hooks: one when a session finishes (`Stop` event) and a different one when it needs your input (`Notification` event).
- Play a sound only when you are away: Windows reports no keyboard or mouse input for 5 minutes, or an AFK switch is on.
- Add an AFK button to the widget header for "near the PC but not using it". It forces the sound on, then turns itself off after a set time (30 minutes until changed).
- Add a setting on the Ledger's Settings page for how long the AFK switch stays on, in whole minutes from 1 to 240.
- The hook reads the AFK state from a small file, so the sounds still work with the widget closed (no file means idle time decides alone).
- Merge sounds that fire close together, so several sessions finishing at once play one sound, and a "needs your input" sound is never hidden by a "finished" one.
- Make the sounds a separate, optional install that does not depend on the toast hooks, the widget or the relay hook.
- Add a "chime hooks" choice to the installer, with the same up-front explanation as the other extras, and the matching uninstall.
- Document it on the Hooks and Widget wiki pages.
- Out of scope, parked in `wiki/Alert-Tiering-Ideas.md`: a delayed reminder when a session sits unanswered, away detection from session activity instead of keyboard and mouse, skipping quick runs, escalation, tray or taskbar signals, speech, and sound on other devices.

## Capabilities

### New Capabilities
- `session-chimes`: the two sounds, when each plays (only when away), the AFK override, and how simultaneous alerts are merged.

### Modified Capabilities
- `installer`: the installer offers the chime hooks as one more separate extra.
- `desktop-widget`: the widget header gets an AFK button that switches the sound override on and off.
- `dashboard-settings`: the Settings page sets how long the AFK switch stays on, and the widget may read that setting.

## Impact

- New script `hooks/chimeScripts/Play-ClaudeChime.ps1`, installed to `%USERPROFILE%\.claude\hooks\chimeScripts\`.
- `hooks/Install-ClaudeHooks.ps1` and `hooks/Uninstall-ClaudeHooks.ps1` gain an `-IncludeChimes` switch, mirroring `-IncludeSessionControl`.
- `Install-Ledger.ps1` gains a `-ChimeHooks` choice.
- Adds `Notification` and `Stop` entries to the user's Claude Code `settings.json`, next to any toast entries.
- The widget's main process, preload bridge, renderer and shared channel list gain the AFK button; it writes a file under the user's Claude Code hooks folder and reads the AFK duration from the backend over loopback, falling back to 30 minutes.
- The backend's settings store, validation, schema and `/api/settings` route gain one value, and the frontend Settings page's "Desktop widget" section gains one field. The existing settings file holds it, so there is no new storage.
- New tests beside `api/tests/test_hook_install.py`, in the settings tests, in `web` and in `widget/tests`; wiki pages `Hooks.md`, `Widget.md`, `Setup-And-Run.md`, `Backend-API-Routes.md`, `Frontend-Shell-And-Theme.md` and `Testing.md` updated.
- No new dependency.
