## RENAMED Requirements

- FROM: `### Requirement: Live sessions are graded by time since start or last compaction`
- TO: `### Requirement: Live sessions are graded by time since latest activity`

## MODIFIED Requirements

### Requirement: Live sessions are graded by time since latest activity
The app SHALL grade each live session by the time elapsed since its latest activity, as `ok` (under 45 minutes), `should` (45 to 55 minutes inclusive) or `needs` (over 55 minutes). A session's latest activity SHALL be the time of the newest request that reached Claude in its main conversation, a tool result sent back counting as one. Requests made by sub-agents SHALL NOT count. When the conversation has no such record, or it cannot be read, the grade SHALL be measured from the session's start. A session's start SHALL be the time of the first record in its conversation, so closing and reopening a session does not restart it; only when the session has no conversation record yet SHALL its start be the time its process started. The app SHALL measure elapsed time against the current time, and SHALL expose the grade, together with the moment the elapsed time is measured from, with each live session so every client shows the same grade. The 45- and 55-minute limits SHALL be fixed and not user-configurable. A session with no known latest activity and no known start time SHALL have no grade.

#### Scenario: Recently started
- **WHEN** a session's latest activity was 20 minutes ago
- **THEN** its grade is `ok`

#### Scenario: Amber band
- **WHEN** a session's latest activity was 50 minutes ago
- **THEN** its grade is `should`

#### Scenario: Boundaries
- **WHEN** a session's latest activity was exactly 45 minutes ago, exactly 55 minutes ago, or 55 minutes and one second ago
- **THEN** its grade is `should`, `should`, and `needs` respectively

#### Scenario: A new prompt restarts the clock
- **WHEN** a session started 3 hours ago, its previous activity was 70 minutes ago, and a prompt was sent 10 minutes ago
- **THEN** its grade is `ok`

#### Scenario: A tool result restarts the clock
- **WHEN** a session's last prompt from the person was 60 minutes ago and a tool result was sent back to Claude 5 minutes ago
- **THEN** its grade is `ok`

#### Scenario: Compaction restarts the clock
- **WHEN** a session was compacted 10 minutes ago and nothing was sent before that for 2 hours
- **THEN** its grade is `ok`

#### Scenario: Only the latest compaction counts
- **WHEN** a session was compacted 2 hours ago and again 50 minutes ago, and nothing was sent after that
- **THEN** its grade is `should`

#### Scenario: Sub-agent requests are ignored
- **WHEN** a session's latest main-conversation activity was 50 minutes ago and a sub-agent it started made requests 5 minutes ago
- **THEN** its grade is `should`

#### Scenario: Unreadable record falls back to the start
- **WHEN** a session's conversation record can't be read and the session started 70 minutes ago
- **THEN** its grade is `needs`

#### Scenario: Grade moves on without new activity
- **WHEN** a session's grade is `ok` and nothing is sent to Claude while it crosses 45 minutes
- **THEN** its grade is `should` at the next refresh

#### Scenario: Unknown start
- **WHEN** a session has no known latest activity and no known start time
- **THEN** it has no grade

#### Scenario: Reopened session keeps its start
- **WHEN** a session's conversation began 50 minutes ago, it has no activity record, and it was closed and reopened 2 minutes ago
- **THEN** its start is the time of the conversation's first record, its grade is `should`, and the Live panel shows that start time

#### Scenario: No conversation record yet
- **WHEN** a session has just been opened, its conversation has no records yet, and its process started 1 minute ago
- **THEN** its start is the time its process started and its grade is `ok`
