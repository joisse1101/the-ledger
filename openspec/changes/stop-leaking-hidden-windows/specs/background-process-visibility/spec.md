## ADDED Requirements

### Requirement: Background processes open no window
A process the Ledger starts to work in the background SHALL run without opening any visible window, including when the default terminal on the PC is Windows Terminal. This covers the chime sound, the open-repo action, the desktop widget launch and the daily history backup. A process the user asked to watch, such as the backend and frontend log windows opened by the start command, is not background and MAY be visible.

#### Scenario: Chime sound with Windows Terminal as the default terminal
- **WHEN** a session finishes while the user is away and Windows Terminal is the default terminal
- **THEN** the sound plays and no window appears at any point

#### Scenario: Open repo window from the dashboard
- **WHEN** the user selects "Open repo window" for a live session
- **THEN** the repository opens and no terminal window appears

#### Scenario: Daily history backup runs
- **WHEN** the scheduled history backup task runs while the user is signed in
- **THEN** the backup completes and no console window appears

### Requirement: A window that still appears names its source
Every background process that has a console SHALL set its window title to `Ledger: <what it is doing>` and print one line saying the same, so that a window that appears anyway tells the user which part of the Ledger opened it. A visible log window opened on purpose SHALL carry a title that names it, such as `Ledger: backend`.

#### Scenario: Chime window slips through
- **WHEN** the sound process shows a window despite the no-window rule
- **THEN** the window title and its one line of text read `Ledger: Playing chimes...`

#### Scenario: Intentional log windows
- **WHEN** the start command opens the backend and frontend windows
- **THEN** their titles read `Ledger: backend` and `Ledger: frontend`

### Requirement: The backup records its run in a log file
Because the history backup has no console, it SHALL write one line starting `Ledger: Backing up history...` to a log file in the app's data folder when it starts, and a line saying whether it succeeded when it ends.

#### Scenario: Backup completes
- **WHEN** the backup task runs and finishes
- **THEN** the log file gains a start line and a success line

#### Scenario: Backup fails
- **WHEN** the backup task runs and fails
- **THEN** the log file gains a start line and a line saying it failed and why

### Requirement: New background processes cannot ship without the no-window rule
The project's automated tests SHALL fail when code in the project starts a process in a way that can open a window and carries no no-window setting.

#### Scenario: A new leaky start is added
- **WHEN** a change adds a process start without a no-window setting
- **THEN** the test run fails and names the file and line
