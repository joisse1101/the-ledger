## Purpose

Lets a live Claude Code session's tool-permission prompts be answered, and its repository opened in
the user's editor, from another device via the dashboard — without changing how the session behaves
when nobody is watching remotely.

## ADDED Requirements

### Requirement: Live sessions relay pending tool-permission decisions
When a live session has the optional relay hook installed and is waiting on a tool-permission
decision, the app SHALL show that pending decision — the tool name and its input — in that session's
control view within a few seconds of it appearing, and SHALL let the user approve or deny it, with an
optional short reason on deny. Approving or denying from the app SHALL resolve the session's actual
local prompt with that choice. A session with the relay hook not installed, or not currently waiting
on a decision, SHALL show no pending decision.

#### Scenario: Decision appears
- **WHEN** a live session with the relay hook installed is about to run a tool that needs permission
- **THEN** its control view shows the tool name, its input, and Approve/Deny controls within a few
  seconds

#### Scenario: Approve resolves the session
- **WHEN** the user approves a pending decision from the app
- **THEN** the waiting session proceeds with that tool call as if it had been approved locally

#### Scenario: Deny with a reason
- **WHEN** the user denies a pending decision and enters a reason
- **THEN** the waiting session receives that reason and does not run the tool

#### Scenario: No relay hook installed
- **WHEN** a live session does not have the relay hook installed
- **THEN** its control view never shows a pending decision, and any local permission prompt behaves
  exactly as it does today

### Requirement: An unanswered decision never blocks the session
A pending decision that is not answered from the app within a bounded wait time, or that can't reach
the app at all, SHALL fall back to the session's normal local prompt, unchanged from today's
behavior. Remote answering SHALL be an optional fast path, never a requirement to continue a session.

#### Scenario: Nobody answers remotely
- **WHEN** a pending decision is not answered from the app before its wait time elapses
- **THEN** the session's normal local permission prompt appears, exactly as if the relay hook were
  not installed

#### Scenario: App isn't running
- **WHEN** a live session's relay hook tries to register a pending decision and the app's backend is
  not running
- **THEN** the session's normal local permission prompt appears without a noticeable delay

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
The app's existing hook installer SHALL offer installing and uninstalling the decision-relay hook as
a choice separate from the toast-notification hooks, so a user can have either, both, or neither.
Instructions for installing it SHALL be documented alongside the toast-hook instructions.

#### Scenario: Install only the relay hook
- **WHEN** the user runs the installer choosing only the relay hook
- **THEN** the relay hook is registered and the toast hooks are not

#### Scenario: Uninstall only the relay hook
- **WHEN** the user runs the uninstaller choosing only the relay hook
- **THEN** the relay hook is removed and any installed toast hooks are left in place
