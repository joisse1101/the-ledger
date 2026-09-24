## MODIFIED Requirements

### Requirement: Session detail is available from either list
Selecting a session in the All list SHALL open a detail view for it: a recap (the title, the last
message from Claude, or the first prompt when there is no last message, the start and last-updated
times, the message count, the estimated cost, and the average tokens per message), the token and
cache history, and the "what filled the context" breakdown defined by the live-context-gauge
capability. If the session's conversation record can't be read, it SHALL say so rather than showing
an empty view. While it is open on a session that is also live, it SHALL update in place as the Live
list refreshes without closing or losing its scroll position. Selecting a session in the **Live
list** instead opens the control view defined by the remote-session-control capability, not this
detail view.

#### Scenario: Open from Live
- **WHEN** the user selects a row in the Live list
- **THEN** the control view defined by the remote-session-control capability opens, not this detail
  view

#### Scenario: Open from All
- **WHEN** the user selects a session in the All list
- **THEN** the detail view opens with the recap above the token history

#### Scenario: Unreadable record
- **WHEN** the selected session's conversation record can't be read
- **THEN** the detail view says it couldn't read the transcript

#### Scenario: Stays open while live
- **WHEN** the detail view is open on a session (opened from the All list) that is also live, and the
  Live list refreshes
- **THEN** the view stays open, its scroll position is kept, and its numbers update

### Requirement: Sessions can be deleted, but not live ones
From the detail view of an All-list session, the user SHALL be able to delete that session's
transcript after an explicit confirmation step that says the action cannot be undone. After deletion
the session SHALL disappear from the All list without a manual refresh. A session that is currently
live SHALL NOT be deletable: the delete control SHALL be replaced by a note saying so, and the server
SHALL refuse a delete request for a live session even if it is made directly. On a device that isn't
the machine running the app, the delete control SHALL NOT be shown at all, since only a local request
can ever delete, and the server SHALL refuse a delete request from such a device even if it is made
directly.

#### Scenario: Confirmed delete
- **WHEN** the user chooses delete on a non-live session and confirms
- **THEN** the transcript is removed from disk and the session no longer appears in the All list

#### Scenario: Cancelled delete
- **WHEN** the user chooses delete and then cancels
- **THEN** nothing is deleted

#### Scenario: Live session
- **WHEN** the user opens the detail view of a session that is also live
- **THEN** there is no delete control and a note says a live session can't be deleted

#### Scenario: Direct request for a live session
- **WHEN** a delete request is made for a live session's ID without going through the UI
- **THEN** the server refuses it and the transcript is left in place

#### Scenario: Remote device sees no delete control
- **WHEN** the detail view is open on a device that isn't the machine running the app
- **THEN** there is no delete control, whether or not the session is live

### Requirement: Projects page lists and deletes projects
The Projects page SHALL list every project Claude Code has been run or trusted in, with its name,
path, trust status, last session ID, CLI version, last cost, last start time, lines added and
removed, and MCP servers. The user SHALL be able to delete a project after an explicit confirmation
step that names the project path and says the action cannot be undone. Deleting SHALL remove the
project's entry from Claude Code's configuration and the project's stored session transcripts, and
the project and its sessions SHALL no longer appear in the app afterwards. On a device that isn't the
machine running the app, the delete control SHALL NOT be shown, since only a local request can ever
delete a project.

#### Scenario: Confirmed project delete
- **WHEN** the user deletes a project and confirms
- **THEN** its configuration entry and stored transcripts are removed and it no longer appears on the
  Projects page or in the All sessions list

#### Scenario: Confirmation names the project
- **WHEN** the user starts deleting a project
- **THEN** the confirmation shows that project's path

#### Scenario: No projects
- **WHEN** Claude Code has no projects recorded
- **THEN** the page says no projects were found

#### Scenario: Remote device sees no delete control
- **WHEN** the Projects page is open on a device that isn't the machine running the app
- **THEN** there is no delete control for any project

## ADDED Requirements

### Requirement: The Remote mode switch is shown only on the machine running the app
The Live list SHALL show Remote mode, whether it is on, and when on how long until it turns itself
off. On the machine running the app it SHALL be a switch the user can flip; on any other device it
SHALL be read-only text with no control, since only a local request can change it.

#### Scenario: Switch on this machine
- **WHEN** the Live list is open on the machine running the app
- **THEN** a Remote mode switch is shown and flipping it turns Remote mode on or off

#### Scenario: Read-only on another device
- **WHEN** the Live list is open on a device that isn't the machine running the app
- **THEN** Remote mode's state is shown as text, with no control to change it
