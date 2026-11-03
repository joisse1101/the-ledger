## ADDED Requirements

### Requirement: The break window is separate from the widget's list window
The widget's break window (see the break-timer capability) SHALL be its own window, able to take clicks, and SHALL NOT resize, move, hide or otherwise change the widget's list window or its tooltip window. Closing the break window SHALL NOT quit the widget. The widget SHALL stay a single instance and SHALL listen on no network port because of it.

#### Scenario: List window untouched
- **WHEN** the break window opens, is used and is closed
- **THEN** the widget's list window keeps its position, size, collapsed state and rows throughout

#### Scenario: Closing does not quit
- **WHEN** the user closes the break window
- **THEN** the widget keeps running and its tray icon stays

#### Scenario: Tooltips still work
- **WHEN** the break window is open and the user hovers the Ledger or Remote button
- **THEN** the tooltip appears as it does without the break window

#### Scenario: Collapsed widget still breaks
- **WHEN** the widget is collapsed to its pill or hidden from the tray and the break is due
- **THEN** the break window still opens

### Requirement: The list window shows the time to the next break
The widget's list window SHALL show the time left until the next break, in minutes and seconds, at the left end of its top bar, to the left of the brightness buttons. The value SHALL come from the same count that opens the break window, SHALL stop moving while the AFK switch is on and look paused, and SHALL return to the full break length when the break window is closed. A new break length from Settings SHALL apply to it.

#### Scenario: Counts down
- **WHEN** the widget has counted 18 minutes of work and the break length is 60
- **THEN** the top bar shows about 42:00 and shows one second less each second

#### Scenario: Paused while AFK
- **WHEN** the AFK switch is on
- **THEN** the shown time does not change and looks paused, and it moves again when AFK is turned off

#### Scenario: Restarts on Close
- **WHEN** the user closes the break window
- **THEN** the top bar shows the full break length again

#### Scenario: Due or open
- **WHEN** a break is due or the break window is open
- **THEN** the top bar shows 0:00

#### Scenario: Follows the break length
- **WHEN** the user lowers the break length in Settings
- **THEN** the shown time reflects the new length from the widget's next read of the setting

#### Scenario: Collapsed widget
- **WHEN** the widget is collapsed to its pill
- **THEN** the count keeps running, and the time is shown again when the widget is expanded
