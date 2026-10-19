## ADDED Requirements

### Requirement: Live sessions are graded by time since start or last compaction
The app SHALL grade each live session by the time elapsed since the later of the session's start and its most recent compaction, as `ok` (under 45 minutes), `should` (45 to 55 minutes inclusive) or `needs` (over 55 minutes). The app SHALL measure elapsed time against the current time, and SHALL expose the grade, together with the moment the elapsed time is measured from, with each live session so every client shows the same grade. The 45- and 55-minute limits SHALL be fixed and not user-configurable. When a session's conversation record is missing or unreadable, the grade SHALL be measured from the session's start alone. A session with no known start time SHALL have no grade.

#### Scenario: Recently started
- **WHEN** a session started 20 minutes ago and has never been compacted
- **THEN** its grade is `ok`

#### Scenario: Amber band
- **WHEN** a session started 50 minutes ago and has never been compacted
- **THEN** its grade is `should`

#### Scenario: Boundaries
- **WHEN** a session is exactly 45 minutes old, exactly 55 minutes old, or 55 minutes and one second old
- **THEN** its grade is `should`, `should`, and `needs` respectively

#### Scenario: Compaction restarts the clock
- **WHEN** a session started 3 hours ago and was compacted 10 minutes ago
- **THEN** its grade is `ok`

#### Scenario: Only the latest compaction counts
- **WHEN** a session was compacted 2 hours ago and again 50 minutes ago
- **THEN** its grade is `should`

#### Scenario: Unreadable record falls back to the start
- **WHEN** a session's conversation record can't be read and the session started 70 minutes ago
- **THEN** its grade is `needs`

#### Scenario: Grade moves on without new activity
- **WHEN** a session's grade is `ok` and no new response is written while it crosses 45 minutes
- **THEN** its grade is `should` at the next refresh

#### Scenario: Unknown start
- **WHEN** a session has no known start time and no compaction
- **THEN** it has no grade

### Requirement: Live list flags sessions that should or need compacting
In the Live sessions list, a session graded `should` SHALL show a "Should compact" pill in amber and a session graded `needs` SHALL show a "Needs compact" pill in red, on its table row and on its card in the narrow layout. A session graded `ok`, or with no grade, SHALL show no pill. The pill SHALL appear and disappear on the list's existing auto-refresh. When the session's status is `idle`, the pill SHALL be shown muted rather than at full strength, with the same wording.

#### Scenario: Amber pill
- **WHEN** a live session is graded `should`
- **THEN** its row or card shows a "Should compact" pill in amber

#### Scenario: Red pill
- **WHEN** a live session is graded `needs`
- **THEN** its row or card shows a "Needs compact" pill in red

#### Scenario: No pill when fine
- **WHEN** a live session is graded `ok` or has no grade
- **THEN** its row or card shows no compact pill

#### Scenario: Pill clears after compaction
- **WHEN** a session showing a pill is compacted
- **THEN** the pill is gone at the next refresh

#### Scenario: Idle session is muted
- **WHEN** a session graded `needs` has status `idle`
- **THEN** it shows a "Needs compact" pill drawn muted

## MODIFIED Requirements

### Requirement: Only absolute token counts are shown
The Live table's Context cell and the detail view SHALL express usage as token counts. The detail view's per-response breakdown MAY additionally show a category's share of that response's own context size as a percentage. Neither SHALL display a percentage of a context window, a context-window size, or a token-based compaction threshold. The time-based compaction grade and its pill are not a token threshold and are allowed.

#### Scenario: No percentage or limit
- **WHEN** the Context cell or the detail view is displayed for any session
- **THEN** no value is presented as a percentage of a context window or limit, and no window size or token threshold is shown

#### Scenario: Live table shows tokens only
- **WHEN** the Live table's Context cell is displayed
- **THEN** it shows token counts only, with no percentage of any kind

#### Scenario: Breakdown share is of the response itself
- **WHEN** the breakdown shows a category's percentage
- **THEN** the percentage is relative to that response's own context size

#### Scenario: Time-based pill beside the token count
- **WHEN** a session's row shows a "Needs compact" pill
- **THEN** its Context cell still shows token counts only
