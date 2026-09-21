# live-context-gauge Specification

## Purpose

Shows how much a running Claude Code session is sending to Claude, in absolute tokens, so the user can tell when a session is getting heavy enough to compact. Includes a per-session detail view of token and cache history and of what filled the context.

## Requirements

### Requirement: Live table shows each session's current context size
The Live sessions table SHALL include a Context column that shows, for each live session, the size of that session's context in tokens. Sizes SHALL be humanised: an exact number below 1,000, the nearest thousand with a `k` suffix from 1,000 up to but below 1,000,000, and one decimal with an `M` suffix at 1,000,000 and above.

#### Scenario: Session with responses shows its context size
- **WHEN** a live session has completed at least one response from Claude
- **THEN** its row's Context cell shows the session's current context size, for example `394k`

#### Scenario: Size is humanised
- **WHEN** a session's context size is 742, 80,618, or 1,234,567 tokens
- **THEN** its Context cell shows `742`, `81k`, or `1.2M` respectively

### Requirement: Context size is everything sent on the latest request
A session's context size SHALL be the total number of tokens in its most recent request to Claude: newly sent input, plus cached tokens read, plus cached tokens written. Activity from subagents SHALL NOT count toward it, and placeholder responses that carry no token usage (such as an API-error message) SHALL be ignored.

#### Scenario: Cached tokens are included
- **WHEN** the latest request had 2 new input tokens, 393,000 cached tokens read, and 1,500 cached tokens written
- **THEN** the context size is 394,502 tokens

#### Scenario: Error placeholder is ignored
- **WHEN** the newest entry of a session is a placeholder response with no token usage, and the response before it had a context size of 210,000
- **THEN** the Context cell shows the size from the earlier real response, not zero

#### Scenario: Subagent activity is excluded
- **WHEN** a session has run subagents
- **THEN** only the main conversation's requests are used to determine the session's context size

### Requirement: Context cell shows recent growth and a trend
When a session has at least two responses, its Context cell SHALL also show the change in context size since the previous response, with a direction marker, and a compact text sparkline of the context size across up to its 24 most recent responses. The sparkline SHALL be scaled from zero to the largest value in that window, not from the window's minimum. When only one response exists, the cell SHALL show the size alone.

#### Scenario: Growing context
- **WHEN** the latest response's context is 2,100 tokens larger than the previous one's
- **THEN** the Context cell shows an upward marker and `+2.1k` next to the size

#### Scenario: Context shrinks after compaction
- **WHEN** the latest response's context is smaller than the previous one's
- **THEN** the Context cell shows a downward marker and the size of the decrease

#### Scenario: Slow growth is not exaggerated
- **WHEN** a session's context grew from 390,000 to 394,000 tokens across its recent responses
- **THEN** the sparkline appears nearly flat, not as a full climb from lowest to highest

#### Scenario: Single response
- **WHEN** a session has exactly one response
- **THEN** the Context cell shows only the size, with no growth figure or sparkline

### Requirement: Only absolute token counts are shown
The Context column and the detail view SHALL express usage only as token counts. They SHALL NOT display a percentage of a context window, a context-window size, or a compaction threshold.

#### Scenario: No percentage or limit
- **WHEN** the Context column or the detail view is displayed for any session
- **THEN** no value is presented as a percentage of a limit, and no limit or threshold is shown

### Requirement: Context stays current with the Live table
The Context value SHALL update on the Live table's existing auto-refresh, and SHALL reflect responses written since the previous refresh without any manual refresh or page reload. It SHALL be available for a brand-new session that no other page yet knows about.

#### Scenario: New response appears on the next refresh
- **WHEN** a live session completes another response while the Live table is auto-refreshing
- **THEN** the session's Context cell shows the new size at the next refresh

#### Scenario: Brand-new session
- **WHEN** a session has only just started and has completed its first response, before any manual refresh of the app's data
- **THEN** its Context cell still shows a context size

### Requirement: Unavailable context degrades to a placeholder
When a session's context size can't be determined (its conversation record is missing or unreadable, or it has no real response yet), its Context cell SHALL show `--` and the row SHALL otherwise render normally. A failure to read one session SHALL NOT affect other rows or the Live table.

#### Scenario: No responses yet
- **WHEN** a live session has not yet received any response from Claude
- **THEN** its Context cell shows `--` and the rest of the row is unchanged

#### Scenario: Unreadable record
- **WHEN** a session's conversation record can't be read
- **THEN** its Context cell shows `--` and all other rows still show their own context sizes

### Requirement: Detail view shows per-response token and cache history
Selecting a live session's row SHALL open a detail view showing, for each of the session's responses in order, the tokens newly sent, the cached tokens read, the cached tokens written, and the output tokens. A response other than the first that wrote more cached tokens than it read SHALL be marked as a cache miss. Each compaction of the conversation SHALL be marked at its position in the history.

#### Scenario: Per-response history is listed
- **WHEN** the user selects a live session's row
- **THEN** the detail view shows new, cache-read, cache-written, and output token counts for each response in order

#### Scenario: Cache miss is marked
- **WHEN** a response wrote 168,000 cached tokens and read 41,000
- **THEN** that response is marked as a cache miss

#### Scenario: Normal cached response is not marked
- **WHEN** a response read 150,000 cached tokens and wrote 500
- **THEN** it is not marked as a cache miss

#### Scenario: First response is never a miss
- **WHEN** a session's first response wrote more cached tokens than it read, as a fresh session's initial prompt typically does
- **THEN** it is not marked as a cache miss

#### Scenario: Compaction is marked
- **WHEN** the conversation was compacted partway through the session
- **THEN** the history shows a compaction marker between the responses before and after it

### Requirement: Detail view shows what filled the context
The detail view SHALL attribute the growth of the session's context to the tool whose result caused it, using the exact change in context size between consecutive responses. Growth that follows a response with no tool call SHALL be attributed to prompts and text. Attribution SHALL cover the period since the session started or since the most recent compaction, and SHALL list the five largest single-response increases with the tool name and a short hint such as the file path or command.

#### Scenario: Attribution reconciles with the current context
- **WHEN** a session has never been compacted
- **THEN** the first response's context size plus the sum of all attributed growth equals the session's current context size

#### Scenario: Growth is grouped by tool
- **WHEN** file reads added 95,000 tokens across the session and shell commands added 97,000
- **THEN** the detail view lists each tool with its total attributed tokens and number of uses

#### Scenario: Largest single increases are listed
- **WHEN** the detail view is shown for a session with more than five growth steps
- **THEN** it lists the five largest single-response increases in descending order, each with tool name and hint

#### Scenario: Attribution restarts after compaction
- **WHEN** the conversation was compacted partway through the session
- **THEN** attribution covers only growth since the first response after the most recent compaction
