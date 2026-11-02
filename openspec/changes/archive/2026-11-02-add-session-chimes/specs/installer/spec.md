# Spec Delta

## MODIFIED Requirements

### Requirement: One installer offers each optional extra
The app SHALL provide one installer that offers, one at a time, the desktop widget shortcut (with the choice of also starting it at sign-in), the toast hooks, the chime hooks, the relay hook, and the daily history backup task. Before each question it SHALL say what the extra does, what it changes on the machine, and what declining means, and it SHALL install only what the user accepts.

#### Scenario: Accepting some extras
- **WHEN** the user accepts the shortcut and the backup task and declines the hooks
- **THEN** the shortcut and the backup task are installed and no hook is installed or changed

#### Scenario: Changes are stated up front
- **WHEN** the installer is about to offer the toast hooks
- **THEN** it first says that it edits the Claude Code settings file and registers a protocol handler

#### Scenario: Chime hooks are stated up front
- **WHEN** the installer is about to offer the chime hooks
- **THEN** it first says that it edits the Claude Code settings file to add sound hooks and copies one script into the user's Claude Code hooks folder

#### Scenario: Chimes without toasts
- **WHEN** the user accepts the chime hooks and declines the toast hooks
- **THEN** the chime hooks are installed and no toast hook or protocol handler is installed

#### Scenario: Declining
- **WHEN** the user declines an extra
- **THEN** nothing for that extra is installed or changed, and the installer moves on to the next
