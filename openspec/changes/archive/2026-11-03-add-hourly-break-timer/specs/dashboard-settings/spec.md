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
- **THEN** it has no settings control, and reads only the setting for how many projects its tooltip lists, the setting for how long its AFK switch stays on, and the setting for its break length

## ADDED Requirements

### Requirement: Settings page sets the break length
The Settings page's "Desktop widget" section SHALL have the number of minutes of work after which the widget opens its break window. The number SHALL be a whole number from 1 to 240, and 60 when never set. A value outside that range, or not a whole number, SHALL be rejected with a message saying why and SHALL leave the stored number unchanged. The section SHALL say that the widget takes a new value within about 30 seconds.

#### Scenario: Default
- **WHEN** the number has never been set
- **THEN** the section shows 60, and the widget opens its break window after 60 minutes of work

#### Scenario: Change the number
- **WHEN** the user sets the number to 45 and saves
- **THEN** the section shows 45 after a reload, and the widget uses 45 minutes within about 30 seconds

#### Scenario: Delay is stated
- **WHEN** the user looks at the break length field
- **THEN** a line beside it says the widget picks up a new value within about 30 seconds

#### Scenario: Out of range rejected
- **WHEN** the user saves 0, 241, or 7.5
- **THEN** the number is not changed and the page explains it must be a whole number from 1 to 240

### Requirement: The break length stays local and independent
The break length SHALL be stored only on the machine running the app, in the same place as the other settings. Saving it SHALL NOT change the other settings, and saving any other setting SHALL NOT change it. Reading or saving it SHALL be refused unless the request is local. A new value SHALL apply to the count already running without restarting the widget.

#### Scenario: Independent of other settings
- **WHEN** the user changes the break length
- **THEN** the worktree folders, the number of projects the widget lists and the AFK duration are unchanged, and changing any of those leaves the break length as it was

#### Scenario: Survives a restart
- **WHEN** the user sets the break length to 45 and the app is restarted
- **THEN** it is still 45

#### Scenario: Remote request refused
- **WHEN** a device on the network reads or saves the number with a valid access token
- **THEN** it is refused and the number is unchanged

#### Scenario: Applies to a count in progress
- **WHEN** the widget has counted 30 minutes of work and the user lowers the break length from 60 to 45
- **THEN** the break window opens after 15 more minutes of work, without restarting the widget

### Requirement: Settings page opens the personal workouts folder
The Settings page's "Desktop widget" section SHALL show the path of the personal workouts folder and an Open folder button that opens that folder in the machine's file manager, creating it first if it is missing. The request SHALL be refused unless it is local, SHALL be enforced by the server, and SHALL open only that one folder.

#### Scenario: Open the folder
- **WHEN** the user presses Open folder in a browser on the machine running the app
- **THEN** the personal workouts folder opens in the file manager

#### Scenario: Folder does not exist yet
- **WHEN** the personal workouts folder is missing and the user presses Open folder
- **THEN** the folder is created and opened

#### Scenario: Remote request refused
- **WHEN** a device on the network asks to open the folder with a valid access token
- **THEN** it is refused and nothing opens

#### Scenario: Open failed
- **WHEN** the file manager cannot be started
- **THEN** the page shows a short message with the folder's path so the user can open it by hand
