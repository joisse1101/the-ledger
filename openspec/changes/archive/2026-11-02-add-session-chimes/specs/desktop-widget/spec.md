# Spec Delta

## ADDED Requirements

### Requirement: Widget has an AFK switch for the session chimes
The widget header SHALL have an AFK button that turns the session chimes' AFK switch on or off, shown as on or off without needing a hover. Turning it on SHALL make the chimes play even while the user is active. It SHALL turn itself off after the AFK duration set in the Ledger's Settings (30 minutes until set), with the button showing off within a few seconds.

#### Scenario: Turn on from the widget
- **WHEN** the user presses an off AFK button
- **THEN** the button shows on and the chimes play for new alerts even if the user keeps using the PC

#### Scenario: Turn off from the widget
- **WHEN** the user presses an on AFK button
- **THEN** the button shows off and the chimes follow idle time alone again

#### Scenario: Expires by itself
- **WHEN** the AFK duration is the default 30 minutes and the AFK button has been on for 30 minutes
- **THEN** the button shows off within a few seconds and the chimes follow idle time alone

#### Scenario: Duration changed in Settings
- **WHEN** the AFK duration is set to 10 minutes and the user then presses an off AFK button
- **THEN** the button turns itself off after 10 minutes, and an AFK switch already on keeps the time it was given

### Requirement: The AFK button appears only when it can work and keeps its state
The AFK button SHALL be shown only when the chime hooks are installed, SHALL keep its state if the widget is restarted, and SHALL work when the backend is unreachable, using the last AFK duration the widget read or 30 minutes. Its hover text SHALL say what a click does and, while on, the time left.

#### Scenario: Chimes not installed
- **WHEN** the chime hooks are not installed
- **THEN** the widget shows no AFK button

#### Scenario: Widget restarted while on
- **WHEN** the widget is closed and reopened 10 minutes after the AFK button was turned on
- **THEN** the button shows on with about 20 minutes left

#### Scenario: Backend unreachable
- **WHEN** the backend is not running and the user presses the AFK button
- **THEN** the AFK state still changes and the button shows it

#### Scenario: Backend unreachable and duration never read
- **WHEN** the backend is not running, the widget has never read the AFK duration, and the user turns the button on
- **THEN** the button turns itself off after 30 minutes
