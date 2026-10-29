## Purpose

Gives the user one place to set up the optional extras on a machine, explaining each before it changes anything, so nothing is installed without the user knowing what it does.

## ADDED Requirements

### Requirement: One installer offers each optional extra
The app SHALL provide one installer that offers, one at a time, the desktop widget shortcut (with the choice of also starting it at sign-in), the toast hooks, the relay hook, and the daily history backup task. Before each question it SHALL say what the extra does, what it changes on the machine, and what declining means, and it SHALL install only what the user accepts.

#### Scenario: Accepting some extras
- **WHEN** the user accepts the shortcut and the backup task and declines the hooks
- **THEN** the shortcut and the backup task are installed and no hook is installed or changed

#### Scenario: Changes are stated up front
- **WHEN** the installer is about to offer the toast hooks
- **THEN** it first says that it edits the Claude Code settings file and registers a protocol handler

#### Scenario: Declining
- **WHEN** the user declines an extra
- **THEN** nothing for that extra is installed or changed, and the installer moves on to the next

### Requirement: Accepting the shortcut also prepares the widget
When the user accepts the widget shortcut, the installer SHALL make sure the widget's dependencies are installed before finishing, so the first launch from the shortcut, which shows no window while it prepares, is not slow or silently broken.

#### Scenario: Shortcut accepted on a clean machine
- **WHEN** the user accepts the shortcut and the widget's dependencies are missing
- **THEN** the installer installs them and creates the shortcut, and the shortcut then starts the widget

### Requirement: An installed relay hook is offered a reinstall
When the relay hook is already installed, the installer SHALL offer to reinstall it, and say that this updates the backend port it uses. When it is not installed, the installer SHALL ask whether to install it.

#### Scenario: Already installed
- **WHEN** the relay hook is installed and the user runs the installer
- **THEN** it offers to reinstall the hook instead of offering a first install

### Requirement: Re-running changes only what is missing or out of date
Running the installer again on a working setup SHALL change nothing that is already current. Each extra's install SHALL be safe to repeat.

#### Scenario: Second run
- **WHEN** the user runs the installer again and accepts everything
- **THEN** no shortcut, hook entry or scheduled task is duplicated, and current ones are left as they are

### Requirement: The backup task has one install route
The daily history backup task SHALL be installed through the installer, and the start command SHALL NOT install it. The existing task SHALL keep working, and the stop command's option to remove it SHALL remain.

#### Scenario: Start command no longer installs the task
- **WHEN** the user runs the start command
- **THEN** no scheduled task is created or changed

### Requirement: Individual install scripts keep working without prompts
Each existing install and uninstall script that the installer uses SHALL keep working on its own and SHALL be callable without asking the user anything, so the installer's questions are the only ones the user sees.

#### Scenario: Script run on its own
- **WHEN** a user runs one of the install scripts directly
- **THEN** it behaves as before and asks no extra questions

#### Scenario: Script called by the installer
- **WHEN** the installer runs an install script for an accepted extra
- **THEN** that script asks the user nothing
