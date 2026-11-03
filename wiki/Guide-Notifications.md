# Guide: Notifications

Get told when a Claude Code session finishes or needs you, without watching the screen.
There are two kinds. A toast is a pop-up in the corner of Windows. A chime is a short sound.
Both are optional and need no dashboard running.

## Install them

1. Run `.\Install-Ledger.ps1` from the repo root. See [Getting started](Guide-Getting-Started.md).
2. Read what each question says it changes before you answer.
3. Answer yes to the toast hooks for pop-ups.
4. Answer yes to the chime hooks for sounds.
5. You can accept one and decline the other.

Both edit your Claude Code settings file. The toast hooks also register a protocol handler. The chime hooks copy one script into your Claude Code hooks folder.

## Read a toast

1. Wait for a pop-up when a session finishes (a "Stop" event) or is waiting for you (a "Notification" event).
2. Read the title and body.
3. Read the third line, `Context 394k` for example. It is how many tokens the session's latest request sent, the same figure as the Context column on the Live page.
4. If the session's record cannot be read, the third line is left out and the toast is otherwise the same.
5. Click the toast to open or focus that session's repository in your editor.

## Hear a chime

1. Step away from the PC.
2. Hear one sound when a session finishes.
3. Hear a different sound when a session needs your input, such as a permission prompt or a question.
4. Know that a chime plays only when you are away. Away means Windows has seen no keyboard or mouse input for a few minutes, or the AFK switch is on.
5. Know that several alerts close together make one sound, and a request for input is never hidden by a finish sound.

## Use the AFK switch

AFK makes chimes play even while you are at the keyboard, for example when you sit nearby but are not working.

1. Open the desktop widget. See [Desktop widget](Guide-Widget.md).
2. Click **AFK** in its top bar. It shows only when the chime hooks are installed.
3. Read a green dot as on and a grey dot as off.
4. Wait for it to turn itself off, or click it again.
5. To change how long it stays on, use **AFK minutes** in [Settings](Guide-Settings.md).
6. Know that the break timer pauses while AFK is on.

## If the two sounds seem alike

Both sounds come from your Windows sound scheme. If they sound the same, check Windows Sound settings.

## Checked and unchecked

- Checked: toast context line, the finished and needs-input sounds, the away rule and the AFK switch against `openspec/specs/toast-context-line/spec.md`, `openspec/specs/session-chimes/spec.md` and `openspec/specs/desktop-widget/spec.md`.
- Checked: control names against `widget/src/renderer/index.html` and `web/src/pages/SettingsPage.tsx`.
- Unchecked: that the two chime sounds are different and audible. The [Hooks](Hooks.md) page says this needs a person listening, and it has not been done.
- Unchecked: the exact look of a toast on screen.
- Unchecked: the exact idle time before you count as away. The spec's rule says 5 minutes and one of its scenarios says 6 minutes, and [Hooks](Hooks.md) says 300 seconds. This page gives no number for that reason.

## More detail

- [Hooks](Hooks.md) explains how the toast, chime and relay hooks work.
- `openspec/specs/toast-context-line/spec.md` and `openspec/specs/session-chimes/spec.md` hold the requirements.
