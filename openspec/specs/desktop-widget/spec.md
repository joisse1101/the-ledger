# desktop-widget Specification

## Purpose

Keeps the user's live Claude Code sessions, with each session's context size and any waiting prompt, visible at all times in a small floating window on the Windows desktop, started with one click or at logon without launching the dashboard's frontend or gateway.

## Requirements

### Requirement: Widget floats above other windows
The widget SHALL be a small frameless window that stays above other application windows, can be dragged to any position, and has a single instance per user session. Its last position SHALL be restored the next time it starts. The widget SHALL provide a way to collapse it to a compact form and expand it again.

#### Scenario: Always visible
- **WHEN** the user focuses another application's window
- **THEN** the widget remains visible above it

#### Scenario: Position is remembered
- **WHEN** the user moves the widget, quits it, and starts it again
- **THEN** it appears at the position the user left it

#### Scenario: Second launch
- **WHEN** the widget is already running and the user launches it again
- **THEN** no second widget appears and the existing one is brought forward

### Requirement: Widget lists live sessions
The widget SHALL list the live sessions the backend reports, one row each, showing the project name and branch, and SHALL keep the list current without user action. A session that stops being live SHALL leave the list. When there are no live sessions the widget SHALL say so.

#### Scenario: Session appears and disappears
- **WHEN** a Claude Code session starts, and later ends
- **THEN** its row appears in the widget within a few seconds of starting and is gone within a few seconds of ending

#### Scenario: No live sessions
- **WHEN** the backend reports no live sessions
- **THEN** the widget shows that there are none instead of an empty window

### Requirement: Each row shows the session's context size
Each row SHALL show the session's context size, using the same value and the same formatting as the Live sessions table and the toast context line, together with the change since the previous response and a direction marker when the session has at least two responses. The widget SHALL show absolute token counts only, with no percentage, window size or threshold. When the size is unavailable the row SHALL show `--` and otherwise render normally.

#### Scenario: Same figure as the Live table
- **WHEN** a session's Context cell in the Live table shows `394k`
- **THEN** its widget row shows `394k` at the same moment

#### Scenario: Growth marker
- **WHEN** the latest response's context is 2,100 tokens larger than the previous one's
- **THEN** the row shows an upward marker and `+2.1k` next to the size

#### Scenario: Context shrinks after compaction
- **WHEN** the latest response's context is smaller than the previous one's
- **THEN** the row shows a downward marker and the size of the decrease

#### Scenario: Size unavailable
- **WHEN** a session has no response yet or its record is unreadable
- **THEN** its row shows `--` and the other rows are unaffected

#### Scenario: No percentages
- **WHEN** any row is displayed
- **THEN** no value is presented as a percentage of a limit and no limit is shown

### Requirement: Rows flag a waiting prompt
A row for a session that has a pending permission prompt or question SHALL be shown in a distinct highlight colour instead of a status icon or badge. The widget SHALL NOT display the prompt's content and SHALL NOT offer to approve, deny or answer an individual prompt. Its only approval-related control is the per-session auto-approve button.

#### Scenario: Prompt is waiting
- **WHEN** a live session has a pending prompt
- **THEN** its row is highlighted and shows no prompt text and no approve, deny or answer controls

#### Scenario: Prompt answered elsewhere
- **WHEN** the prompt is answered in the terminal or the dashboard
- **THEN** the highlight is gone at the next refresh

### Requirement: Clicking a row opens the session's repo window
Clicking a session's row SHALL open or focus the editor window for that session's repository, the same action a toast click performs. If it fails because the session is no longer live, the widget SHALL show a brief message and otherwise keep working.

#### Scenario: Click focuses the window
- **WHEN** the user clicks a live session's row and an editor window for its repo is open
- **THEN** that window is focused

#### Scenario: Click opens the window
- **WHEN** the user clicks a row and no editor window for its repo is open
- **THEN** a new editor window for the repo opens

#### Scenario: Session ended before the click
- **WHEN** the session ended between the last refresh and the click
- **THEN** the widget shows a brief message and the list refreshes

### Requirement: Widget reports an unreachable backend
When the backend cannot be reached, the widget SHALL show an offline state in place of the list, keep retrying, and recover on its own when the backend returns. It SHALL NOT show stale rows as if they were current.

#### Scenario: Backend is down
- **WHEN** the backend is not running
- **THEN** the widget shows that it is offline and no session rows

#### Scenario: Backend comes back
- **WHEN** the backend starts while the widget is showing the offline state
- **THEN** the widget shows the live sessions again without being restarted

### Requirement: Tray menu provides secondary actions
The widget SHALL have a system tray icon whose menu offers: open the Ledger dashboard, start the backend, show or hide the widget, and quit. Opening the dashboard SHALL start the frontend if it is not already running and then open the dashboard in the browser, and SHALL NOT start the gateway. Quitting SHALL close the widget and stop only the processes the widget itself started.

#### Scenario: Open the dashboard on demand
- **WHEN** the user chooses "Open Ledger" while the frontend is not running
- **THEN** the frontend is started and the dashboard opens in the browser, and the gateway container is not started

#### Scenario: Frontend already running
- **WHEN** the user chooses "Open Ledger" while the frontend is already running
- **THEN** the dashboard opens in the browser and no second frontend is started

#### Scenario: Quit leaves foreign processes alone
- **WHEN** the backend was already running before the widget started and the user quits the widget
- **THEN** the backend keeps running

#### Scenario: Quit stops what the widget started
- **WHEN** the widget started the backend and the user quits the widget
- **THEN** that backend process is stopped

### Requirement: One-click startup brings up only what the widget needs
A start script SHALL start the backend with no visible console window, only if it is not already running, and then launch the widget. It SHALL NOT start the frontend or the gateway container. Before launching it SHALL check that the widget's packages and Electron binary are actually present and current, install or rebuild them when they are not, and stop with an error when that fails. It SHALL use the same backend and frontend ports as the main start command. The project SHALL provide a way to create a desktop shortcut that runs it, and a way to enable and disable running it at logon.

#### Scenario: Cold start from the shortcut
- **WHEN** nothing is running and the user runs the desktop shortcut
- **THEN** the backend and the widget are running, with no console window left open, and neither the frontend nor the gateway is running

#### Scenario: Backend already running
- **WHEN** the backend is already running and the user runs the shortcut
- **THEN** only the widget is started, and no second backend is started

#### Scenario: Widget dependencies empty or incomplete
- **WHEN** the widget's packages folder exists but is empty, or the Electron binary is missing, and the user runs the shortcut
- **THEN** the missing pieces are installed first and the widget then starts

#### Scenario: Same ports as the main start
- **WHEN** the main start command has chosen and saved the backend port and the user runs the shortcut
- **THEN** the widget uses that port

#### Scenario: Logon autostart
- **WHEN** logon autostart is enabled and the user signs in
- **THEN** the backend and widget start without further action

#### Scenario: Autostart disabled
- **WHEN** the user disables logon autostart
- **THEN** nothing starts at the next sign-in, and the desktop shortcut keeps working

### Requirement: Widget reaches the backend as a local client only
The widget SHALL talk to the backend only over the loopback interface, SHALL NOT require or store the access token, and SHALL NOT expose any listening port of its own.

#### Scenario: Loopback only
- **WHEN** the widget is running
- **THEN** its requests go to the backend on this machine and it listens on no network port

### Requirement: Widget can turn Remote mode on and off
The widget SHALL have a Remote mode toggle that turns the app's Remote mode on or off through the
backend, with the same effect as the toggle on the Ledger's Live list, including starting what is
needed for other devices to connect and closing it again when turned off. The widget SHALL start
neither the container runtime nor the gateway itself. The toggle SHALL show Remote mode's state
(off, starting, ready, or failed) without needing a hover, and SHALL stay in step with changes made
elsewhere, such as from the Ledger or by the 8 hour expiry.

#### Scenario: Turn on from the widget
- **WHEN** the user turns the widget's Remote mode toggle on while the gateway is stopped
- **THEN** the toggle shows starting, then ready once other devices can connect

#### Scenario: Turn off from the widget
- **WHEN** the user turns the toggle off
- **THEN** Remote mode is off and the gateway is stopped, as if turned off in the Ledger

#### Scenario: Changed elsewhere
- **WHEN** Remote mode is turned on or off in the Ledger, or expires after 8 hours
- **THEN** the widget's toggle shows the new state within a few seconds

#### Scenario: Cannot start
- **WHEN** Remote mode fails to start
- **THEN** the toggle shows failed and the reason is available in the tooltip

### Requirement: Hovering the Remote button shows Remote mode status and the sign-in code
While Remote mode is starting, ready, or failed, hovering the widget's Remote button SHALL show a
small tooltip window next to the widget, without resizing the widget and without taking focus. It
SHALL show a message for the current step while starting, such as starting Docker or starting the
gateway, and the reason when failed. When ready it SHALL show the scannable sign-in code on an
opaque background that does not follow the widget's transparency setting, the gateway's address
under it without the token, and the time left. It SHALL hide when the pointer leaves, and SHALL
appear by itself for a few seconds when Remote mode becomes ready. While Remote mode is off,
hovering the Remote button SHALL show no code. Hovering the Ledger button SHALL NOT show Remote
mode status or the sign-in code.

#### Scenario: Hover while ready
- **WHEN** Remote mode is ready and the user hovers the Remote button
- **THEN** the tooltip shows the scannable code, the address under it without the token, and the
  time left, and it disappears when the pointer leaves

#### Scenario: Hover while starting
- **WHEN** Remote mode is starting and the user hovers the Remote button
- **THEN** the tooltip shows what is being started, and no code

#### Scenario: Appears on ready
- **WHEN** Remote mode becomes ready
- **THEN** the tooltip appears by itself for a few seconds so the code can be scanned, then hides

#### Scenario: Off
- **WHEN** Remote mode is off and the user hovers the Remote button
- **THEN** no code is shown

#### Scenario: Ledger button does not show the code
- **WHEN** Remote mode is ready and the user hovers the Ledger button
- **THEN** the sign-in code is not shown

#### Scenario: Transparent widget
- **WHEN** the widget's transparency is set low
- **THEN** the code is still drawn on an opaque background and stays scannable

### Requirement: Rows have an auto-approve button
Each live session row SHALL have a button at its right end that turns the session's auto-approve on or
off through the app, shown as on or off. Pressing it SHALL NOT open the session's repo window. The
button SHALL be shown only once the app reports that a prompt has been relayed since it started, and
SHALL reflect the state set from the Ledger within a refresh. Its hover text SHALL say what a click
does.

#### Scenario: Turn on from the widget
- **WHEN** the user presses an off auto-approve button on a row
- **THEN** auto-approve is on for that session, the button shows on, and the repo window is not opened

#### Scenario: Turn off from the widget
- **WHEN** the user presses an on auto-approve button
- **THEN** auto-approve is off for that session and the button shows off

#### Scenario: Hook not seen yet
- **WHEN** the app reports that no prompt has been relayed since it started
- **THEN** no row shows an auto-approve button

#### Scenario: Changed in the Ledger
- **WHEN** auto-approve is switched for a session in the Ledger
- **THEN** that row's button shows the new state at the next refresh

### Requirement: Rows show a compact-state dot
Each session row SHALL show a dot to the left of the row's content, coloured by the session's compact grade, using the same grade the Live sessions list uses: green for `ok`, amber for `should` and red for `needs`. The dot SHALL be drawn at full opacity regardless of the widget's transparency setting. When the session's status is `idle`, the dot SHALL be drawn as a hollow ring in the same colour instead of a filled dot. A session with no grade SHALL show no dot but keep its row aligned with the other rows. The dot SHALL carry no text, and clicking the row SHALL behave as before.

#### Scenario: Fresh session
- **WHEN** a live session is graded `ok`
- **THEN** its row shows a filled green dot at its left

#### Scenario: Should compact
- **WHEN** a live session is graded `should`
- **THEN** its row shows a filled amber dot at its left

#### Scenario: Needs compact
- **WHEN** a live session is graded `needs`
- **THEN** its row shows a filled red dot at its left

#### Scenario: Idle session
- **WHEN** a session graded `needs` has status `idle`
- **THEN** its dot is a hollow red ring

#### Scenario: Same grade as the Live list
- **WHEN** the Live sessions list shows a "Should compact" pill for a session
- **THEN** that session's widget dot is amber at the same moment

#### Scenario: No grade
- **WHEN** a session has no grade
- **THEN** its row shows no dot and its name stays aligned with the other rows

### Requirement: Row tints follow the widget's transparency setting
The highlight colours that tint a row (a waiting prompt, a finished session, an error status) SHALL follow the widget's transparency setting in the same way the widget's background does, while the row's text and the compact-state dot stay fully opaque.

#### Scenario: Transparent widget
- **WHEN** the widget's transparency is set low and a row is tinted
- **THEN** the tint is as see-through as the widget's background, the row's text is fully readable, and the dot is fully opaque

#### Scenario: Solid widget
- **WHEN** the widget is fully opaque
- **THEN** tinted rows look the same as before

### Requirement: Hovering the Ledger button shows the projects' open issues and pull requests
Hovering the widget's Ledger button SHALL show a tooltip window next to the widget, without resizing
the widget and without taking focus, listing the projects hosted on GitHub. Each row SHALL show the
project's name, its source (GitHub), its open issue count and its open pull request count, with `--`
for a count that is unavailable. Projects SHALL be ordered by open issues plus open pull requests,
most first, a project with unavailable counts after those with counts, and ties in the order the
backend lists them. At most the configured number of projects SHALL be shown (5 unless set
otherwise), followed by a line giving how many more there are. Projects that are not on GitHub, and
projects that are not git repos, SHALL NOT be listed. The tooltip SHALL hide when the pointer leaves.
It SHALL be shown whatever Remote mode's state, on an opaque background that does not follow the
widget's transparency setting.

#### Scenario: Hover shows the top projects
- **WHEN** seven GitHub projects are known, the configured number is 5, and the user hovers the
  Ledger button
- **THEN** the five with the most open issues plus pull requests are listed, each with its name,
  source, issues and pull requests, followed by "+2 more"

#### Scenario: Non-GitHub and non-repo projects are left out
- **WHEN** a project has no git remote, or its remote is not on GitHub
- **THEN** it is not listed

#### Scenario: Unavailable counts
- **WHEN** a GitHub project's counts cannot be read
- **THEN** its row shows `--` for issues and pull requests and is listed after the projects with counts

#### Scenario: No GitHub projects
- **WHEN** no known project is hosted on GitHub and the user hovers the Ledger button
- **THEN** the tooltip says there are no GitHub projects

#### Scenario: Leaves with the pointer
- **WHEN** the pointer leaves the Ledger button
- **THEN** the tooltip hides

#### Scenario: Independent of Remote mode
- **WHEN** Remote mode is off, starting, ready, or failed and the user hovers the Ledger button
- **THEN** the projects list is shown, not Remote status

### Requirement: The projects list is kept current without delaying the hover
The widget SHALL read the projects' repo info and the configured number at startup, about every
minute, and on every hover of the Ledger button, and SHALL NOT wait for a read before showing the
tooltip: a hover shows the last known rows at once, and rows that arrive while the tooltip is open
SHALL replace them in place. Before the first read has finished, the tooltip SHALL say it is
loading. When a read fails, the last known rows SHALL stay shown. When no read has ever succeeded,
the tooltip SHALL say the projects could not be loaded. The widget SHALL NOT ask the backend to
rescan or to drop its caches for this. If the configured number cannot be read, the widget SHALL use 5.

#### Scenario: Hover shows cached rows at once
- **WHEN** the rows were read a minute ago and the user hovers the Ledger button
- **THEN** the tooltip appears with those rows without waiting, and a read starts in the background

#### Scenario: Newer rows replace the shown ones
- **WHEN** a read finishes while the tooltip is open and the counts changed
- **THEN** the tooltip shows the new counts without being closed

#### Scenario: Before the first read
- **WHEN** the user hovers the Ledger button before the first read has finished
- **THEN** the tooltip says the projects are loading

#### Scenario: Backend unreachable
- **WHEN** the backend does not answer
- **THEN** the last known rows stay shown, or the tooltip says the projects could not be loaded if there never were any

#### Scenario: Setting unreadable
- **WHEN** the configured number cannot be read
- **THEN** at most 5 projects are shown
