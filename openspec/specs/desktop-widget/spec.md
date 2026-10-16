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
A row for a session that has a pending permission prompt or question SHALL be shown in a distinct highlight colour instead of a status icon or badge. The widget SHALL NOT display the prompt's content and SHALL NOT offer to approve, deny or answer it.

#### Scenario: Prompt is waiting
- **WHEN** a live session has a pending prompt
- **THEN** its row is highlighted and shows no prompt text or answer controls

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
A start script SHALL start the backend with no visible console window, only if it is not already running, and then launch the widget. It SHALL NOT start the frontend or the gateway container. The project SHALL provide a way to create a desktop shortcut that runs it, and a way to enable and disable running it at logon.

#### Scenario: Cold start from the shortcut
- **WHEN** nothing is running and the user runs the desktop shortcut
- **THEN** the backend and the widget are running, with no console window left open, and neither the frontend nor the gateway is running

#### Scenario: Backend already running
- **WHEN** the backend is already running and the user runs the shortcut
- **THEN** only the widget is started, and no second backend is started

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

### Requirement: Hovering the Ledger button shows Remote mode status and the sign-in code
While Remote mode is starting, ready, or failed, hovering the widget's Ledger button SHALL show a
small tooltip window next to the widget, without resizing the widget and without taking focus. It
SHALL show a message for the current step while starting, such as starting Docker or starting the
gateway, and the reason when failed. When ready it SHALL show the scannable sign-in code on an
opaque background that does not follow the widget's transparency setting, the gateway's address
under it without the token, and the time left. It SHALL hide when the pointer leaves, and SHALL
appear by itself for a few seconds when Remote mode becomes ready. While Remote mode is off,
hovering SHALL show no code.

#### Scenario: Hover while ready
- **WHEN** Remote mode is ready and the user hovers the Ledger button
- **THEN** the tooltip shows the scannable code, the address under it without the token, and the
  time left, and it disappears when the pointer leaves

#### Scenario: Hover while starting
- **WHEN** Remote mode is starting and the user hovers the Ledger button
- **THEN** the tooltip shows what is being started, and no code

#### Scenario: Appears on ready
- **WHEN** Remote mode becomes ready
- **THEN** the tooltip appears by itself for a few seconds so the code can be scanned, then hides

#### Scenario: Off
- **WHEN** Remote mode is off and the user hovers the Ledger button
- **THEN** no code is shown

#### Scenario: Transparent widget
- **WHEN** the widget's transparency is set low
- **THEN** the code is still drawn on an opaque background and stays scannable
