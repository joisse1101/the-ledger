# session-chimes Specification

## Purpose

Plays a short sound when a Claude Code session finishes or needs the user's input, but only when the user is away from the PC, so the user notices without looking at the screen and is not nagged while working. It stays quiet when several alerts arrive together.

## Requirements

### Requirement: A finished session plays the finished sound
When a Claude Code session finishes its work and stops while the user is away, a short sound SHALL play on this PC.

#### Scenario: Session finishes while the user is away
- **WHEN** a session finishes and the user has not used the keyboard or mouse for 5 minutes
- **THEN** the finished sound plays once

### Requirement: A session that needs input plays a different sound
When a Claude Code session needs the user's input, such as a permission prompt or a question, while the user is away, a short sound SHALL play that the user can tell apart from the finished sound.

#### Scenario: Session asks for permission while the user is away
- **WHEN** a session is waiting for the user's answer and the user has not used the keyboard or mouse for 5 minutes
- **THEN** the needs-input sound plays once, and it is not the finished sound

### Requirement: Sound only when the user is away
A sound SHALL play only when the user is away, meaning Windows reports no keyboard or mouse input for at least 5 minutes, or the AFK switch is on. A sound SHALL NOT play while the user has used the keyboard or mouse within the last 5 minutes and the AFK switch is off, whichever window or repo they are in. If the idle time cannot be read, the user SHALL be treated as away.

#### Scenario: User is at the PC
- **WHEN** a session finishes and the user used the mouse 1 minute ago
- **THEN** no sound plays, even if the session's repo window is not the focused window

#### Scenario: Just short of away
- **WHEN** a session finishes and the last keyboard or mouse input was 4 minutes 59 seconds ago
- **THEN** no sound plays

#### Scenario: Just reaching away
- **WHEN** a session finishes and the last keyboard or mouse input was 5 minutes ago
- **THEN** the finished sound plays

#### Scenario: Idle time cannot be read
- **WHEN** a session finishes and the system cannot report the idle time
- **THEN** the finished sound plays

### Requirement: The AFK switch forces the sound until it expires
While the AFK switch is on, a sound SHALL play for alerts even if the user is using the keyboard or mouse. The switch SHALL turn itself off after the AFK duration the user chose, 30 minutes until changed, counted from when it was turned on. When the switch is off, expired, or has never been set, idle time alone SHALL decide, and the sounds SHALL work with no widget or dashboard running.

#### Scenario: Near the PC but not using it
- **WHEN** the user turns the AFK switch on, moves the mouse, and a session finishes 1 minute later
- **THEN** the finished sound plays

#### Scenario: Switch expires
- **WHEN** the AFK duration is the default 30 minutes, the switch was turned on 31 minutes ago, the user is active, and a session finishes
- **THEN** no sound plays

#### Scenario: Shorter duration chosen
- **WHEN** the AFK duration is set to 10 minutes, the switch was turned on 11 minutes ago, the user is active, and a session finishes
- **THEN** no sound plays

#### Scenario: No switch set
- **WHEN** the AFK switch has never been set and the user is active
- **THEN** idle time alone decides, and no sound plays

### Requirement: Alerts that arrive together make one sound
Alerts for any sessions that arrive within 5 seconds of a sound SHALL be merged: a finished alert SHALL be skipped if any sound played in that time, and a needs-input alert SHALL be skipped only if a needs-input sound played in that time. A needs-input alert SHALL never be hidden by a finished sound.

#### Scenario: Several sessions finish together
- **WHEN** three sessions finish within 5 seconds of each other while the user is away
- **THEN** the finished sound plays once

#### Scenario: Needs-input follows a finish
- **WHEN** a session finishes and another needs input 2 seconds later while the user is away
- **THEN** both the finished sound and the needs-input sound play

#### Scenario: Finish follows needs-input
- **WHEN** a session needs input and another finishes 2 seconds later while the user is away
- **THEN** only the needs-input sound plays

### Requirement: A failing sound never disturbs Claude Code
Playing a sound SHALL NOT delay a session, change its behavior, print anything for Claude Code to read, open any window, or report a failure. The chime hook itself SHALL print nothing. The separate process that plays the sound is not read by Claude Code, so it SHALL identify itself as `Ledger: Playing chimes...` as `background-process-visibility` requires. If a sound cannot be played, the session SHALL carry on as if no sound had been requested.

#### Scenario: Sound cannot play
- **WHEN** the sound fails to play, for example because no audio device is available
- **THEN** the session is unaffected and nothing is reported to it

#### Scenario: Sound plays on a PC whose default terminal is Windows Terminal
- **WHEN** the finished sound plays while the user is away
- **THEN** no window appears, and the hook prints nothing to Claude Code

### Requirement: Sounds work without the toasts or the dashboard
The sounds SHALL be installable and SHALL work whether or not the toast hooks, the relay hook, the widget or the backend are installed or running.

#### Scenario: Chimes only
- **WHEN** only the chime hooks are installed, the dashboard is not running and the user is away
- **THEN** sessions still play the finished and needs-input sounds
