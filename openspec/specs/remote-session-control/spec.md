## Purpose

Lets a live Claude Code session's blocking prompts (tool-permission dialogs and questions) be
answered from the dashboard, on the PC or from another device, and its repository opened in the
user's editor from another device - without ever changing what the terminal shows or accepts.

## Requirements

### Requirement: Live sessions relay blocking prompts to the dashboard
When a live session has the optional relay hook installed and is waiting on a blocking prompt - a
tool-permission dialog, or a multiple-choice question Claude asked - the app SHALL show that pending
prompt in that session's control view within a few seconds of it appearing, and SHALL show a waiting
indicator on the session's Live list row. For a permission prompt it SHALL show the tool name and its
input and let the user approve, or deny with an optional short reason. For a question it SHALL show
each question with its real options, and let the user pick one option, several when the question
allows multiple, or enter their own text. Answering from the app SHALL resolve the session's actual
prompt with that answer. A session with the relay hook not installed, or not currently waiting on a
prompt, SHALL show no pending prompt.

#### Scenario: Permission prompt appears
- **WHEN** a live session with the relay hook installed is waiting on a tool-permission dialog
- **THEN** its Live row shows a waiting indicator, and its control view shows the tool name, its
  input, and Approve/Deny controls within a few seconds

#### Scenario: Question appears
- **WHEN** a live session with the relay hook installed is waiting on a question from Claude
- **THEN** its control view shows the question(s) with their options, and controls to pick an
  option, pick several where allowed, or type an answer

#### Scenario: Approve resolves the session
- **WHEN** the user approves a pending permission prompt from the app
- **THEN** the waiting session proceeds with that tool call as if it had been approved in the
  terminal

#### Scenario: Deny with a reason
- **WHEN** the user denies a pending permission prompt and enters a reason
- **THEN** the waiting session receives that reason and does not run the tool

#### Scenario: Answer a question
- **WHEN** the user answers a pending question from the app
- **THEN** the waiting session receives exactly that answer and continues, as if it had been given
  in the terminal

#### Scenario: No relay hook installed
- **WHEN** a live session does not have the relay hook installed
- **THEN** its control view never shows a pending prompt, and its terminal dialogs behave exactly as
  they do today

### Requirement: Whichever surface answers first wins
A pending prompt SHALL be answerable from the session's own terminal dialog, from the dashboard on
the machine running the app, and (while Remote mode is on) from the dashboard on another device. The
first answer SHALL resolve the prompt and the session SHALL continue; every other surface SHALL then
stop offering that prompt. An answer that arrives after the prompt was already resolved SHALL be
refused with a message that the session already moved on, and SHALL NOT affect the session.

#### Scenario: Answered in the terminal
- **WHEN** the user answers a prompt in the session's terminal dialog
- **THEN** the session continues, and within a few seconds the dashboard no longer shows that prompt
  on any device

#### Scenario: Answered from the dashboard
- **WHEN** the user answers a prompt from the dashboard, on this machine or another device
- **THEN** the session continues as if answered locally, and the terminal dialog goes away

#### Scenario: Too late
- **WHEN** a device submits an answer for a prompt that was already resolved elsewhere
- **THEN** it is told the session already moved on, and the session is unaffected

### Requirement: An unanswered prompt never blocks or alters the session
The terminal dialog SHALL always be shown and answerable, whether or not the relay hook is
installed, the app is running, or Remote mode is on. A prompt that is not answered from the app, or a
relay that can't reach the app at all, SHALL leave the terminal dialog as the only way to answer,
unchanged from today's behavior. Remote answering SHALL be an optional extra path, never a
requirement to continue a session.

#### Scenario: Nobody answers from the app
- **WHEN** a pending prompt is not answered from the app
- **THEN** the terminal dialog stays on screen and works exactly as if the relay hook were not
  installed

#### Scenario: App isn't running
- **WHEN** a live session's relay hook tries to register a prompt and the app's backend is not
  running
- **THEN** the terminal dialog appears without a noticeable delay and nothing is held back

### Requirement: Remote mode controls what other devices can do
The app SHALL have a Remote mode that the user turns on before leaving the machine. While it is on,
a device other than the machine running the app that presents the access token SHALL be able to see
a session's pending prompts and answer them. While it is off, such a device SHALL see no pending
prompts and any attempt to answer one SHALL be refused, while the machine's own browser and the
terminal are unaffected. Only a request from the machine running the app SHALL be able to turn
Remote mode on or off; other devices SHALL be able to see whether it is on but not change it, even
with a valid token. Remote mode SHALL turn itself off after 8 hours, and after the app's backend
restarts.

#### Scenario: Remote mode off
- **WHEN** Remote mode is off and a session is waiting on a prompt
- **THEN** another device sees no pending prompt and cannot answer one, while this machine's
  dashboard and the terminal can

#### Scenario: Remote mode on
- **WHEN** Remote mode is on and a session is waiting on a prompt
- **THEN** another device with the access token sees the prompt and can answer it

#### Scenario: Another device tries to switch it
- **WHEN** a device other than the machine running the app tries to turn Remote mode on or off,
  with or without a valid token
- **THEN** it is refused and Remote mode is unchanged, and the switch is not shown on that device

#### Scenario: Expiry
- **WHEN** Remote mode has been on for 8 hours, or the backend restarts
- **THEN** it is off again

### Requirement: A live session's repo can be opened from the app
The control view of a live session SHALL offer a button that opens that session's repository in the
user's editor on the machine running the app, using the same window-focus-or-launch behavior already
used when a desktop toast notification is clicked. The repository path SHALL be the session's own
recorded working directory, never a path supplied by the request.

#### Scenario: Repo already open
- **WHEN** the user selects "Open repo window" for a session whose repository is already open in the
  editor
- **THEN** that editor window is focused, and no duplicate window opens

#### Scenario: Repo not open yet
- **WHEN** the user selects "Open repo window" for a session whose repository is not open in the
  editor
- **THEN** a new editor window opens for that repository

### Requirement: The relay hook installs and uninstalls independently of the toast hooks
The app's existing hook installer SHALL offer installing and uninstalling the prompt-relay hook as a
choice separate from the toast-notification hooks, so a user can have either, both, or neither.
Installing it SHALL also remove any earlier tool-call-based relay hook the app previously
installed. Instructions for installing it SHALL be documented alongside the toast-hook instructions.

#### Scenario: Install only the relay hook
- **WHEN** the user runs the installer choosing only the relay hook
- **THEN** the relay hook is registered and the toast hooks are not

#### Scenario: Earlier relay hook present
- **WHEN** the user installs the relay hook on a machine that has the earlier tool-call-based relay
  installed
- **THEN** the earlier one is removed and only the new one remains

#### Scenario: Uninstall only the relay hook
- **WHEN** the user runs the uninstaller choosing only the relay hook
- **THEN** the relay hook is removed and any installed toast hooks are left in place
