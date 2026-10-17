## ADDED Requirements

### Requirement: The Live session panel has an auto-approve switch
The Live session panel (control view) SHALL show an auto-approve switch beside the session's title
that turns auto-approve on or off for that session, and SHALL show the most recent automatically
approved prompt. The switch SHALL be shown only on the machine running the app and only once the app
reports that a prompt has been relayed since it started. A device other than the machine running the
app SHALL see the state but no switch.

#### Scenario: Switch on the PC
- **WHEN** a prompt has been relayed since the app started and the user opens a live session's panel on
  the machine running the app
- **THEN** the panel shows the auto-approve switch beside the title, and flipping it changes the
  session's auto-approve

#### Scenario: Other device
- **WHEN** the panel is opened from another device
- **THEN** it shows whether auto-approve is on but offers no switch

#### Scenario: Hook not seen yet
- **WHEN** no prompt has been relayed since the app started
- **THEN** the panel shows no auto-approve switch

### Requirement: The Live sessions list shows which sessions auto-approve
The Live sessions list, and no other list, SHALL have an "Auto-approve" column that marks each session
whose auto-approve is on. The column SHALL be shown only once the app reports that a prompt has been
relayed since it started.

#### Scenario: Marked rows
- **WHEN** auto-approve is on for a live session
- **THEN** its row in the Live list is marked in the Auto-approve column, and rows with it off are not

#### Scenario: Column hidden before the hook is seen
- **WHEN** no prompt has been relayed since the app started
- **THEN** the Live list shows no Auto-approve column

#### Scenario: Other lists
- **WHEN** the All sessions list is shown
- **THEN** it has no Auto-approve column
