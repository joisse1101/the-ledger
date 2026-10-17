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
The app SHALL have a Remote mode that the user turns on before leaving the machine. Turning it on
SHALL make the app reachable from other devices: it SHALL start whatever is not already running that
other devices need (the container runtime, the web interface, and the network gateway), and it SHALL
report its state as off, starting, ready, or failed with a reason. It SHALL be ready only once other
devices can actually connect, and SHALL NOT be reported as on while nothing is listening. While it is
ready, a device other than the machine running the app that presents the access token SHALL be able
to see a session's pending prompts and answer them. While it is off, the network gateway SHALL be
stopped, such a device SHALL see no pending prompts and any attempt to answer one SHALL be refused,
while the machine's own browser and the terminal are unaffected. Only a request from the machine
running the app SHALL be able to turn Remote mode on or off; other devices SHALL be able to see its
state but not change it, even with a valid token. Remote mode SHALL turn itself off after 8 hours,
and after the app's backend restarts. Whenever it turns off, the gateway SHALL be stopped, and so
SHALL the web interface if Remote mode started it; a web interface that was already running SHALL be
left running.

#### Scenario: Remote mode off
- **WHEN** Remote mode is off and a session is waiting on a prompt
- **THEN** another device sees no pending prompt and cannot answer one, the gateway is not running,
  and this machine's dashboard and the terminal still work

#### Scenario: Remote mode on
- **WHEN** Remote mode is ready and a session is waiting on a prompt
- **THEN** another device with the access token sees the prompt and can answer it

#### Scenario: Turning on from nothing
- **WHEN** the container runtime, the web interface and the gateway are all stopped and the user
  turns Remote mode on
- **THEN** Remote mode reports starting while each is brought up in turn, and ready once another
  device can connect

#### Scenario: Something cannot start
- **WHEN** the user turns Remote mode on and a step fails or does not finish in a reasonable time,
  such as the container runtime not being installed
- **THEN** Remote mode reports failed with the reason, is not reported as on, and anything it
  already started is stopped

#### Scenario: Another device tries to switch it
- **WHEN** a device other than the machine running the app tries to turn Remote mode on or off,
  with or without a valid token
- **THEN** it is refused and Remote mode is unchanged, and the switch is not shown on that device

#### Scenario: Expiry
- **WHEN** Remote mode has been on for 8 hours, or the backend restarts
- **THEN** it is off again and the gateway is stopped, including a gateway left running by an
  earlier backend

#### Scenario: Turning off closes only what it opened
- **WHEN** Remote mode is turned off after it started the web interface
- **THEN** the gateway and the web interface it started are stopped

#### Scenario: Web interface was already running
- **WHEN** the web interface was running before Remote mode was turned on, and Remote mode is turned
  off
- **THEN** the gateway is stopped and the web interface keeps running

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
