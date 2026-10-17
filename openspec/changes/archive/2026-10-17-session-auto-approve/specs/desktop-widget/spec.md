## MODIFIED Requirements

### Requirement: Rows flag a waiting prompt
A row for a session that has a pending permission prompt or question SHALL be shown in a distinct highlight colour instead of a status icon or badge. The widget SHALL NOT display the prompt's content and SHALL NOT offer to approve, deny or answer an individual prompt. Its only approval-related control is the per-session auto-approve button.

#### Scenario: Prompt is waiting
- **WHEN** a live session has a pending prompt
- **THEN** its row is highlighted and shows no prompt text and no approve, deny or answer controls

#### Scenario: Prompt answered elsewhere
- **WHEN** the prompt is answered in the terminal or the dashboard
- **THEN** the highlight is gone at the next refresh

## ADDED Requirements

### Requirement: Rows have an auto-approve button
Each live session row SHALL have a button at its right end that turns the session's auto-approve on or
off through the app, shown as on or off. Pressing it SHALL NOT open the session's repo window. The
button SHALL be shown only once the app reports that a prompt has been relayed since it started, and
SHALL reflect the state set from the Ledger within a refresh. Its hover text SHALL say what a click
does.

#### Scenario: Turn on from the widget
- **WHEN** the user presses an off auto-approve button on a row
- **THEN** auto-approve is on for that session, the button shows on, and the repo window is not opened

#### Scenario: Turn off from the widget
- **WHEN** the user presses an on auto-approve button
- **THEN** auto-approve is off for that session and the button shows off

#### Scenario: Hook not seen yet
- **WHEN** the app reports that no prompt has been relayed since it started
- **THEN** no row shows an auto-approve button

#### Scenario: Changed in the Ledger
- **WHEN** auto-approve is switched for a session in the Ledger
- **THEN** that row's button shows the new state at the next refresh
