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
- **THEN** it has no settings control, and reads only the setting for how many projects its tooltip lists

## ADDED Requirements

### Requirement: Settings page sets how many projects the widget's tooltip lists
The Settings page SHALL have a "Desktop widget" section with the number of projects the widget's
Ledger-button tooltip lists. The number SHALL be a whole number from 1 to 10, and 5 when never set.
A value outside that range, or not a whole number, SHALL be rejected with a message saying why and
SHALL leave the stored number unchanged. Saving it SHALL take effect for the widget on its next
read, within about a minute, without restarting anything, and SHALL NOT change the worktree-folder
list or how sessions are attributed. Saving the worktree folders SHALL NOT change the stored number,
and saving the number SHALL NOT change the folders. The number SHALL be stored only on the machine
running the app, in the same place as the other settings.

#### Scenario: Default
- **WHEN** the number has never been set
- **THEN** the section shows 5, and the widget lists at most 5 projects

#### Scenario: Change the number
- **WHEN** the user sets the number to 3 and saves
- **THEN** the section shows 3 after a reload, and the widget lists at most 3 projects once it next
  reads the setting

#### Scenario: Out of range rejected
- **WHEN** the user saves 0, 11, or 2.5
- **THEN** the number is not changed and the page explains it must be a whole number from 1 to 10

#### Scenario: Independent of worktree folders
- **WHEN** the user adds a worktree folder after setting the number to 3
- **THEN** the number is still 3, and when the user then changes the number the folders are unchanged

#### Scenario: Survives a restart
- **WHEN** the user sets the number to 3 and the app is restarted
- **THEN** the number is still 3

#### Scenario: Remote request refused
- **WHEN** a device on the network reads or saves the number with a valid access token
- **THEN** it is refused and the number is unchanged
