## ADDED Requirements

### Requirement: A live session can auto-approve its plain permission prompts
The app SHALL let the user switch auto-approve on or off for one live session at a time. While it is
on for a session, a pending permission prompt of that session SHALL be approved by the app without
waiting for a person, as if the user had approved it, and the terminal dialog SHALL go away. Only a
plain permission prompt SHALL be auto-approved: a question from Claude (multiple-choice or free text)
and a plan-approval prompt SHALL NOT be, and SHALL wait for a person exactly as they do with
auto-approve off. A shell command prompt whose command matches a known-dangerous pattern (for
example privilege escalation such as `sudo`, recursive or forced deletion, forced git pushes and
hard resets, piping a download into a shell, disk formatting, or shutdown) SHALL also wait for a
person, as SHALL a shell command prompt whose command text cannot be read. Switching it on SHALL also approve the plain permission prompts that are already
pending for that session. Auto-approve SHALL be off for a session by default, SHALL turn itself off
when the session is no longer live, after 8 hours, and after the app's backend restarts. It SHALL NOT
affect any other session. Only a request from the machine running the app SHALL be able to switch it;
other devices SHALL be able to see its state but not change it, even with a valid token.

#### Scenario: Plain permission prompt is approved
- **WHEN** auto-approve is on for a live session and it reaches a tool-permission dialog
- **THEN** the session proceeds with that tool call without any person answering, and the dialog goes
  away

#### Scenario: Question still waits
- **WHEN** auto-approve is on and the session asks a multiple-choice or free-text question
- **THEN** the question stays pending until a person answers it

#### Scenario: Plan approval still waits
- **WHEN** auto-approve is on and the session asks for approval of a plan
- **THEN** the prompt stays pending until a person answers it

#### Scenario: Dangerous command still waits
- **WHEN** auto-approve is on and the session asks permission to run a shell command such as
  `sudo apt install x`, `rm -rf build`, or `git push --force`
- **THEN** the prompt stays pending until a person answers it, and the same session's ordinary
  commands such as `npm test` are still approved automatically

#### Scenario: Unreadable command still waits
- **WHEN** auto-approve is on and a shell command prompt arrives without readable command text
- **THEN** the prompt stays pending until a person answers it

#### Scenario: Prompt already pending when switched on
- **WHEN** a session is waiting on a plain permission prompt and the user switches auto-approve on
  for it
- **THEN** that prompt is approved at once

#### Scenario: Other sessions are unaffected
- **WHEN** auto-approve is on for one session and a different session reaches a permission dialog
- **THEN** the other session's dialog stays pending

#### Scenario: It ends by itself
- **WHEN** a session with auto-approve on is no longer live, 8 hours pass, or the backend restarts
- **THEN** auto-approve is off for that session

#### Scenario: Another device tries to switch it
- **WHEN** a device other than the machine running the app tries to switch auto-approve, with or
  without a valid token
- **THEN** it is refused and the state is unchanged, and the switch is not shown on that device

### Requirement: Auto-approve is offered only once the relay hook has been seen
The app SHALL offer the auto-approve switch only after at least one prompt has been relayed to it
since the backend started, because without the relay hook no prompt ever reaches the app and
auto-approve could never act. Until then no auto-approve switch, button or column SHALL be shown
anywhere. Once a prompt has been relayed, the switch SHALL be offered for every live session until
the backend restarts.

#### Scenario: No prompt relayed yet
- **WHEN** the backend has started and no session has had a prompt relayed to it
- **THEN** the Ledger and the widget show no auto-approve control

#### Scenario: First prompt unlocks every session
- **WHEN** any live session has a prompt relayed to the app
- **THEN** the auto-approve control becomes available for all live sessions, including ones that have
  not had a prompt

#### Scenario: Backend restarts
- **WHEN** the backend restarts
- **THEN** the auto-approve control is hidden again until the next prompt is relayed

### Requirement: Auto-approved prompts are visible
The app SHALL show, for each live session, whether auto-approve is on, and SHALL show in the session's
control view the most recent prompt it approved automatically (the tool name and when), so the user can
see what was approved on their behalf.

#### Scenario: Last auto-approved prompt
- **WHEN** a session with auto-approve on has had a prompt approved automatically
- **THEN** its control view shows the tool name and time of the latest one

#### Scenario: Nothing approved yet
- **WHEN** auto-approve is on but nothing has been approved automatically
- **THEN** no auto-approved line is shown
