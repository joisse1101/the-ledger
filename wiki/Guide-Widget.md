# Guide: Desktop widget

Keep your live sessions in a small floating window above your other windows, and get a reminder to take a break.
The widget runs on Windows only. It talks to the Ledger on your PC and nothing else.

## Start the widget

1. Run `.\Start-Ledger.ps1`. It starts the widget with the dashboard. See [Getting started](Guide-Getting-Started.md).
2. Or run `.\Install-Ledger.ps1`, accept the widget shortcut, then open "Ledger Widget" from your desktop.
3. To start it when you sign in to Windows, accept the autostart question in the installer.
4. A second launch just brings the running widget forward.

## Read the list

1. Look at the top bar. It shows a summary of the live sessions.
2. Read one row per session, with its project and branch, and its context size. See [Live sessions](Guide-Live-Sessions.md) for what context means.
3. Read a number such as `+2.1k` and an arrow as how much the context grew or shrank since the last response.
4. Read `--` as "not known".
5. Read a coloured dot at the left of a row as the compact grade: green is fine, amber is "should compact", red is "needs compact". A hollow dot means the session is idle. See [Compact](Glossary.md#compact).
6. Read a warm background as a prompt waiting on you. The widget never shows the prompt itself. Answer it in the terminal or the dashboard.
7. If the widget shows an offline state, the backend is not running. It recovers by itself when the backend returns.

## Use the buttons

1. Click a row to open or focus that session's repository in your editor.
2. Click the **Auto** button at the end of a row to turn [auto-approve](Glossary.md#auto-approve) on or off for that session. It appears only after the dashboard has seen a relayed prompt.
3. Click **Remote** to turn [Remote mode](Glossary.md#remote-mode) on or off. Hover it while it is on to see the sign-in QR code, the address and the time left.
4. Click **AFK** to make the chime sounds play even while you use the PC. See [Notifications](Guide-Notifications.md). The button shows only when the chime hooks are installed.
5. Hover the Ledger button (it opens the dashboard) to see your GitHub projects with open issue and pull request counts.
6. Click the two sun buttons to make the window more or less see-through.
7. Click the dash button to collapse the widget to one line, and again to expand it.
8. Drag the window to move it. It remembers where you left it.
9. Right-click the tray icon for **Open Ledger**, **Start backend**, show or hide, and **Quit**.

## Take a break

1. Read the countdown at the left of the top bar. It shows the time to the next break as minutes and seconds.
2. Read a paused look as AFK being on. The count only advances while AFK is off.
3. When the count ends, a break window opens above your other windows. It does not take the keyboard.
4. Read the workout's name. Nothing plays yet.
5. Click **Start** to play the workout, a video or a series of timed images.
6. Click **Skip** to get a different workout. It waits for **Start** again.
7. Click **Close** to finish. The count starts again from zero.
8. If there are no workouts, the window says so and only **Close** works.

To change the break length, or to add your own workout videos and images, see [Settings](Guide-Settings.md).

## Checked and unchecked

- Checked: control names (**Auto**, **Remote**, **AFK**, **Open Ledger**, **Start**, **Skip**, **Close**) against `widget/src/renderer/index.html`, `widget/src/renderer/view.ts` and `widget/src/renderer/breakView.ts`, and the behaviour against `openspec/specs/desktop-widget/spec.md` and `openspec/specs/break-timer/spec.md`.
- Unchecked: the tray menu item names, taken from [Widget](Widget.md) and the spec, not from the tray source.
- Unchecked: the shortcut's exact name "Ledger Widget", taken from [Widget](Widget.md).
- Unchecked: the break window's button after a workout finishes. The source shows "Play again" in place of **Start**.
- Unchecked: the widget was not launched, so nothing here was seen on screen.

## More detail

- [Widget](Widget.md) explains how the widget is built.
- `openspec/specs/desktop-widget/spec.md` and `openspec/specs/break-timer/spec.md` hold the requirements.
