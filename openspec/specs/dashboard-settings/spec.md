# dashboard-settings Specification

## Purpose

Lets the user configure the dashboard from the machine running it, starting with which folders inside
a repo hold its worktrees, so sessions in those worktrees are counted under their repo.

## Requirements

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

### Requirement: Settings requests require a local request
Reading or changing settings SHALL be refused unless the request comes from the machine the app runs
on, using the same locality test the rest of the app uses. This SHALL apply even when the request
carries a valid access token, and SHALL be enforced by the server, not only by hiding the page.

#### Scenario: Local request succeeds
- **WHEN** a browser on the machine running the app reads or saves settings
- **THEN** it proceeds normally, without needing a token

#### Scenario: Remote request refused even with a valid token
- **WHEN** a device on the network reads or saves settings and presents the correct access token
- **THEN** it is refused and the settings are unchanged

### Requirement: One list of worktree folders applies to every repo
The Settings page SHALL show one list of worktree folders, each a path relative to a repo root, that
applies to every repo. A session that started in `<repo>/<folder>/<name>`, for any folder in the
list, SHALL be treated everywhere in the app as a session in the worktree `<name>` of `<repo>`. A
session SHALL be matched to the outermost repo path that fits.

#### Scenario: Session in an added folder counts toward its repo
- **WHEN** `.trees` is in the list and a session started in `C:/repos/the-ledger/.trees/fix-nav`
- **THEN** it is shown as a session in the worktree `fix-nav` of the project `the-ledger`, and no
  `fix-nav` project is shown

#### Scenario: Session that moved deeper still counts
- **WHEN** `.trees` is in the list and a session started in `C:/repos/the-ledger/.trees/fix-nav/web`
- **THEN** it is shown as a session in the worktree `fix-nav` of the project `the-ledger`

#### Scenario: Nested folder
- **WHEN** `tools/wt` is in the list and a session started in `C:/repos/app/tools/wt/spike`
- **THEN** it is shown as a session in the worktree `spike` of the project `app`

#### Scenario: Folder not in the list
- **WHEN** `.trees` is not in the list and a session started in `C:/repos/the-ledger/.trees/fix-nav`
- **THEN** it is not treated as a worktree session

### Requirement: Claude Code's own worktree folder is always included
The list SHALL always include `.claude/worktrees`, shown as built in. The user SHALL NOT be able to
remove it, and a saved list SHALL never drop it.

#### Scenario: Built-in entry cannot be removed
- **WHEN** the user views the worktree-folder list
- **THEN** `.claude/worktrees` is listed as built in, with no control to remove it

#### Scenario: Nothing configured yet
- **WHEN** no folder has ever been added
- **THEN** the list holds only `.claude/worktrees`, and worktree sessions are recognised exactly as
  before this capability existed

### Requirement: Worktree folders are validated
A folder SHALL be accepted only as a relative path inside a repo: not empty, not absolute (no drive
letter, no leading `/` or `\`), and with no `.` or `..` segment. Backslashes SHALL be stored as `/`
and leading or trailing slashes trimmed. A folder that is already in the list SHALL NOT be added
twice. A rejected folder SHALL leave the list unchanged and say why.

#### Scenario: Backslashes are normalised
- **WHEN** the user adds `tools\wt\`
- **THEN** the list shows `tools/wt`

#### Scenario: Path outside the repo rejected
- **WHEN** the user adds `../shared`, `C:/trees`, or `/trees`
- **THEN** the folder is not added and the page explains it must be a path inside the repo

#### Scenario: Duplicate rejected
- **WHEN** the user adds `.trees` while `.trees` is already in the list
- **THEN** the list is unchanged and the page says the folder is already listed

### Requirement: Saved folders persist and take effect at once
A saved list SHALL survive restarts of the app and SHALL take effect without one: the next read
after a save SHALL reflect the new list, including sessions recorded before the save. The settings
SHALL be stored only on the machine running the app and SHALL NOT be committed to the repository.

#### Scenario: Earlier sessions move under their repo
- **WHEN** the user adds `.trees` while sessions from `C:/repos/the-ledger/.trees/fix-nav` are already
  listed as a `fix-nav` project
- **THEN** after saving, without a restart, those sessions are shown under `the-ledger` with the
  worktree `fix-nav`

#### Scenario: List survives a restart
- **WHEN** the user adds `.trees` and the app is restarted
- **THEN** the list still includes `.trees`

### Requirement: Removing a folder undoes its attributions
Removing a folder SHALL take effect at once and fully undo adding it: every session in that folder,
whether its transcript is still on disk or only preserved in the durable store, SHALL stop being a
worktree session and SHALL be shown as a project named after its worktree folder, as it was before
the folder was added. Sessions in folders still in the list SHALL be unaffected.

#### Scenario: Removal moves sessions back
- **WHEN** the user removes `.trees` after sessions from `C:/repos/the-ledger/.trees/fix-nav` were
  shown under `the-ledger`
- **THEN** after saving, without a restart, those sessions are shown as a `fix-nav` project with no
  worktree, including sessions whose transcripts were already pruned from disk

#### Scenario: Add then remove leaves no trace
- **WHEN** the user adds `.trees`, saves, then removes it and saves again
- **THEN** every session is attributed exactly as it was before `.trees` was added

#### Scenario: Other folders are unaffected
- **WHEN** the user removes `.trees` while `.claude/worktrees` sessions exist
- **THEN** the `.claude/worktrees` sessions keep their worktree and repo project

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
