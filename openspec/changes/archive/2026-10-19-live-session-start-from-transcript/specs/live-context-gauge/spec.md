## MODIFIED Requirements

### Requirement: Live sessions are graded by time since start or last compaction
The app SHALL grade each live session by the time elapsed since the later of the session's start and its most recent compaction, as `ok` (under 45 minutes), `should` (45 to 55 minutes inclusive) or `needs` (over 55 minutes). A session's start SHALL be the time of the first record in its conversation, so closing and reopening a session does not restart it; only when the session has no conversation record yet SHALL its start be the time its process started. The app SHALL measure elapsed time against the current time, and SHALL expose the grade, together with the moment the elapsed time is measured from, with each live session so every client shows the same grade. The 45- and 55-minute limits SHALL be fixed and not user-configurable. When a session's conversation record is missing or unreadable, the grade SHALL be measured from the session's start alone. A session with no known start time SHALL have no grade.

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

#### Scenario: Reopened session keeps its start
- **WHEN** a session's conversation began 50 minutes ago, it was closed and reopened 2 minutes ago, and it has never been compacted
- **THEN** its start is the time of the conversation's first record, its grade is `should`, and the Live panel shows that start time

#### Scenario: No conversation record yet
- **WHEN** a session has just been opened, its conversation has no records yet, and its process started 1 minute ago
- **THEN** its start is the time its process started and its grade is `ok`
