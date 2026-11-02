# Spec Delta

## MODIFIED Requirements

### Requirement: Settings page is shown only on the machine running the app
The app SHALL offer a Settings page whose navigation entry is shown only to a browser on the machine
running the app, using the same locality test the rest of the app uses. No other device SHALL see the
entry, and opening the Settings address from another device SHALL show the default page. The desktop
widget SHALL NOT show or change settings; it MAY read a setting that governs its own display, as a
local client.

#### Scenario: Local browser sees Settings
- **WHEN** the dashboard is opened in a browser on the machine running the app
- **THEN** the navigation shows a Settings entry that opens the Settings page

#### Scenario: Another device does not see Settings
- **WHEN** a device on the network opens the dashboard through the gateway, signed in with a valid
  access token
- **THEN** the navigation has no Settings entry, and opening the Settings address shows the default
  page

#### Scenario: Widget reads but does not offer settings
- **WHEN** the desktop widget is running
- **THEN** it has no settings control, and reads only the setting for how many projects its tooltip lists and the setting for how long its AFK switch stays on

## ADDED Requirements

### Requirement: Settings page sets how long the widget's AFK switch stays on
The Settings page's "Desktop widget" section SHALL have the number of minutes the widget's AFK switch stays on after it is turned on. The number SHALL be a whole number from 1 to 240, and 30 when never set. A value outside that range, or not a whole number, SHALL be rejected with a message saying why and SHALL leave the stored number unchanged.

#### Scenario: Default
- **WHEN** the number has never been set
- **THEN** the section shows 30, and the AFK switch turns itself off 30 minutes after it is turned on

#### Scenario: Change the number
- **WHEN** the user sets the number to 10 and saves
- **THEN** the section shows 10 after a reload, and the next time the AFK switch is turned on it lasts 10 minutes

#### Scenario: Out of range rejected
- **WHEN** the user saves 0, 241, or 7.5
- **THEN** the number is not changed and the page explains it must be a whole number from 1 to 240

### Requirement: The AFK duration applies to the next switch-on and stays local
A saved AFK duration SHALL apply the next time the AFK switch is turned on, and SHALL NOT change a switch that is already on. It SHALL be stored only on the machine running the app, SHALL be independent of the other settings, and reading or saving it SHALL be refused unless the request is local.

#### Scenario: Switch already on
- **WHEN** the AFK switch is on and the user saves a different number
- **THEN** the running switch keeps the time it was given

#### Scenario: Independent of other settings
- **WHEN** the user changes this number
- **THEN** the worktree folders and the number of projects the widget lists are unchanged, and changing either of those leaves this number as it was

#### Scenario: Remote request refused
- **WHEN** a device on the network reads or saves the number with a valid access token
- **THEN** it is refused and the number is unchanged
