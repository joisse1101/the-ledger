## MODIFIED Requirements

### Requirement: A failing sound never disturbs Claude Code
Playing a sound SHALL NOT delay a session, change its behavior, print anything for Claude Code to read, open any window, or report a failure. The chime hook itself SHALL print nothing. The separate process that plays the sound is not read by Claude Code, so it SHALL identify itself as `Ledger: Playing chimes...` as `background-process-visibility` requires. If a sound cannot be played, the session SHALL carry on as if no sound had been requested.

#### Scenario: Sound cannot play
- **WHEN** the sound fails to play, for example because no audio device is available
- **THEN** the session is unaffected and nothing is reported to it

#### Scenario: Sound plays on a PC whose default terminal is Windows Terminal
- **WHEN** the finished sound plays while the user is away
- **THEN** no window appears, and the hook prints nothing to Claude Code
