# dashboard-settings Specification

## Purpose

Lets the user configure the dashboard from the machine running it, starting with which folders inside
a repo hold its worktrees, so sessions in those worktrees are counted under their repo.

## Requirements

### Requirement: Settings page is shown only on the machine running the app
The app SHALL offer a Settings page whose navigation entry is shown only to a browser on the machine
running the app, using the same locality test the rest of the app uses. No other device SHALL see the
entry, and opening the Settings address from another device SHALL show the default page. The desktop
widget SHALL NOT offer settings.

#### Scenario: Local browser sees Settings
- **WHEN** the dashboard is opened in a browser on the machine running the app
- **THEN** the navigation shows a Settings entry that opens the Settings page

#### Scenario: Another device does not see Settings
- **WHEN** a device on the network opens the dashboard through the gateway, signed in with a valid
  access token
- **THEN** the navigation has no Settings entry, and opening the Settings address shows the default
  page

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
