# toast-context-line Specification

## Purpose

Adds the session's current context size to the Claude Code Notification and Stop toasts, so the user can see at a glance how much is being sent to Claude, and falls back to the existing toast whenever that figure can't be determined.

## Requirements

### Requirement: Toasts show the session's context size
When a Notification or Stop toast is shown for a session whose conversation record can be read, the toast SHALL include a third line of the form `Context <n>` beneath the existing title and body lines, where `<n>` is the session's current context size in tokens.

#### Scenario: Stop toast
- **WHEN** a session finishes a task and its conversation record shows a context size of 394,000 tokens
- **THEN** the toast shows its usual title and body, plus a third line `Context 394k`

#### Scenario: Notification toast
- **WHEN** a session is waiting for input and its conversation record shows a context size of 97,000 tokens
- **THEN** the toast shows its usual title and body, plus a third line `Context 97k`

### Requirement: Context size is everything sent on the latest request
The context size shown SHALL be the total number of tokens in the session's most recent request to Claude: newly sent input, plus cached tokens read, plus cached tokens written. Subagent activity SHALL NOT count toward it, and placeholder responses that carry no token usage (such as an API-error message) SHALL be ignored. The number SHALL be humanised: exact below 1,000, the nearest thousand with a `k` suffix from 1,000 up to but below 1,000,000, and one decimal with an `M` suffix at 1,000,000 and above.

#### Scenario: Cached tokens are included
- **WHEN** the latest request had 2 new input tokens, 393,000 cached tokens read, and 1,500 cached tokens written
- **THEN** the third line reads `Context 395k`

#### Scenario: Error placeholder is ignored
- **WHEN** the newest entry in the record is a placeholder response with no token usage, and the response before it had a context size of 210,000
- **THEN** the third line reads `Context 210k`, not `Context 0`

#### Scenario: Large sizes
- **WHEN** the context size is 1,234,567 tokens
- **THEN** the third line reads `Context 1.2M`

### Requirement: Toast agrees with the live gauge
For the same session at the same moment, the context size on the toast SHALL be the same number, computed by the same definition and formatted the same way, as the Context column of the app's Live sessions table.

#### Scenario: Same session, same figure
- **WHEN** a session's Context cell in the Live table shows `394k` and one of its toasts is shown at that moment
- **THEN** the toast's third line reads `Context 394k`

### Requirement: Missing context omits the line
When the session's conversation record can't be located or read, or it contains no response with token usage, the toast SHALL be shown exactly as it is without this feature: title and body only, with no third line and no error.

#### Scenario: Hook input without a conversation record
- **WHEN** the hook input identifies only the working directory and gives no conversation-record location
- **THEN** the toast shows only the title and body

#### Scenario: Missing file
- **WHEN** the hook input names a conversation record that does not exist
- **THEN** the toast shows only the title and body

#### Scenario: No responses yet
- **WHEN** the conversation record has no response with token usage
- **THEN** the toast shows only the title and body

### Requirement: Token lookup never delays or breaks the toast
The toast SHALL always be shown, whatever happens while looking up the context size. The lookup SHALL NOT wait for the conversation record to change and SHALL NOT retry. The toast's title, body, and click behavior (focusing or opening the repository's editor window) SHALL be unchanged.

#### Scenario: Lookup fails
- **WHEN** reading the conversation record raises an error partway through
- **THEN** the toast is still shown with its title and body

#### Scenario: Click behavior is unchanged
- **WHEN** the user clicks a toast that includes the context line
- **THEN** the repository's editor window is focused or opened, as for a toast without the line

### Requirement: Reading is non-intrusive
Determining the context size SHALL only read the conversation record. It SHALL work while the session is still writing to it, and SHALL NOT modify or lock the record in a way that interferes with the running session.

#### Scenario: Session is still running
- **WHEN** a toast fires while the session is still appending to its conversation record
- **THEN** the context size is read successfully and the running session is unaffected
