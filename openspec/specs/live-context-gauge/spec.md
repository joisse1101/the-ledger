# live-context-gauge Specification

## Purpose

Shows how much a running Claude Code session is sending to Claude, in absolute tokens, so the user can tell when a session is getting heavy enough to compact. Includes a per-session detail view of token and cache history and of what filled the context.

## Requirements

### Requirement: Live table shows each session's current context size
The Live sessions list SHALL include, for each live session, a Context cell showing the size of that session's context in tokens. In the table layout the Context cell is a column; in the card layout used on narrow screens it is a labelled field on the session's card. Sizes SHALL be humanised: an exact number below 1,000, the nearest thousand with a `k` suffix from 1,000 up to but below 1,000,000, and one decimal with an `M` suffix at 1,000,000 and above.

#### Scenario: Session with responses shows its context size
- **WHEN** a live session has completed at least one response from Claude
- **THEN** its row's or card's Context cell shows the session's current context size, for example `394k`

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
The Live table's Context cell and the detail view SHALL express usage as token counts. The detail view's per-response breakdown MAY additionally show a category's share of that response's own context size as a percentage. Neither SHALL display a percentage of a context window, a context-window size, or a compaction threshold.

#### Scenario: No percentage or limit
- **WHEN** the Context cell or the detail view is displayed for any session
- **THEN** no value is presented as a percentage of a context window or limit, and no window size or threshold is shown

#### Scenario: Live table shows tokens only
- **WHEN** the Live table's Context cell is displayed
- **THEN** it shows token counts only, with no percentage of any kind

#### Scenario: Breakdown share is of the response itself
- **WHEN** the breakdown shows a category's percentage
- **THEN** the percentage is relative to that response's own context size

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
Selecting a live session's row or card SHALL open a detail view showing, for each of the session's responses in order, the tokens newly sent, the cached tokens read, the cached tokens written, and the output tokens. A response other than the first that wrote more cached tokens than it read SHALL be marked as a cache miss. Each compaction of the conversation SHALL be marked at its position in the history.

#### Scenario: Per-response history is listed
- **WHEN** the user selects a live session's row or card
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

### Requirement: Each response has a context breakdown that adds up to its exact size
For every response, the detail view SHALL be able to show that response's context split into categories whose sizes sum to the response's exact context size: the estimated startup categories (memory files, skills, custom agents, MCP instructions), the exact growth added since the start of the current segment credited to each tool (and to prompts and text), and a remainder row labelled to cover the system prompt, built-in tools and any compaction summary. A segment starts at the session's first response or at the first response after a compaction. The remainder SHALL be derived as the exact context size minus the other rows, never estimated independently, and SHALL NOT be negative.

#### Scenario: Rows add up
- **WHEN** a response's breakdown is shown
- **THEN** the sizes of all rows, including the remainder row, sum to that response's context size

#### Scenario: Estimates larger than the first response are scaled down
- **WHEN** the estimated startup categories sum to more than the first response's context in the segment
- **THEN** each estimated category is scaled down proportionally so that they sum to no more than that context, and the remainder row is zero

#### Scenario: Growth rows are exact
- **WHEN** file reads added 95,000 tokens and shell commands added 97,000 between the first response of the segment and the selected response
- **THEN** the breakdown lists those tools with 95,000 and 97,000 tokens

#### Scenario: Breakdown restarts after compaction
- **WHEN** the conversation was compacted before the selected response
- **THEN** its growth rows cover only the period since the first response after the most recent compaction, and the compaction summary is part of the remainder row

### Requirement: Startup categories are estimated from the transcript and applied as they change
The startup categories SHALL be estimated from the content Claude Code recorded in the session's transcript for memory files, the skill listing, custom agents and MCP instructions, applying later additions and removals recorded in the transcript so that each response reflects what was loaded at that point. Each category SHALL be itemised (each memory file, skill, agent and MCP server with its own estimate), and the items of a category SHALL sum to the category's size. A session whose transcript records no content for a category SHALL show that category as absent, not as zero estimated.

#### Scenario: Items sum to their category
- **WHEN** a category with several items is shown
- **THEN** the item sizes sum to the category's size

#### Scenario: Skill added mid-session
- **WHEN** the transcript records a skill added after the third response
- **THEN** responses before the fourth do not include that skill and later responses do

#### Scenario: No recorded content
- **WHEN** a session's transcript records no custom agent listing
- **THEN** its breakdown has no custom agents category

### Requirement: Estimated figures are labelled approximate
Every estimated figure in the breakdown SHALL be presented as approximate, in both the hover and the pinned views, and the exact figures (the response's context size and the growth rows) SHALL be distinguishable from the estimated ones. The remainder row SHALL state what it contains.

#### Scenario: Estimate is labelled
- **WHEN** the hover tooltip or the pinned panel shows a startup category
- **THEN** it is marked as an estimate

#### Scenario: Exact figures are not marked as estimates
- **WHEN** the breakdown shows the response's context size or a tool's growth
- **THEN** those figures are not marked as estimates

### Requirement: Hovering a response shows a compact breakdown
Hovering a response's bar in the tokens-per-response chart SHALL show that response's context size and its largest categories, each with its token count and its share of that response's own context. The tooltip SHALL show categories only, not items.

#### Scenario: Tooltip lists top categories
- **WHEN** the user hovers a response's bar
- **THEN** a tooltip shows the response's context size and its largest categories with tokens and percentage of that response's context

#### Scenario: Percentages are of the response's own context
- **WHEN** the tooltip shows a category of 6,700 tokens for a response whose context is 28,300 tokens
- **THEN** its share is shown as 24%

### Requirement: Selecting a response pins a full breakdown panel
Clicking or tapping a response's bar SHALL pin a panel under the chart showing every category of that response's breakdown with tokens and share of the response's context. Each category with items SHALL be expandable to its items. The panel SHALL be absent until a bar is selected, SHALL show categories collapsed by default, SHALL work without hover, and SHALL be dismissable. Selecting another bar SHALL replace the panel's response.

Note (known limitation, accepted): on a session that is still live, hover works but clicking a bar to pin the panel has been observed not to work, and a fix was tried (building the replacement chart hidden and swapping it in) without success. It is deliberately left as is; selection is only expected to work on sessions that are not live.

#### Scenario: Select a bar
- **WHEN** the user clicks or taps a response's bar
- **THEN** a panel for that response appears under the chart, listing all categories collapsed

#### Scenario: Expand a category
- **WHEN** the user expands the skills category in the panel
- **THEN** each skill is listed with its estimated size

#### Scenario: Every response is selectable however many there are
- **WHEN** a session has hundreds of responses and the user hovers or clicks anywhere in a response's column of the chart
- **THEN** that response is the one hovered or selected, not only when the pointer is exactly on its thin bar

#### Scenario: Selected bar is highlighted
- **WHEN** a response's panel is pinned
- **THEN** that response's bar is visually distinguished from the others, and the distinction is removed when the panel is dismissed

#### Scenario: Hover details are visible over the modal
- **WHEN** the user hovers a bar inside the session detail modal
- **THEN** the tooltip is displayed above the modal, not beneath it

#### Scenario: Select another bar
- **WHEN** a panel is pinned and the user selects a different bar
- **THEN** the panel shows the newly selected response

#### Scenario: Dismiss
- **WHEN** the user dismisses the panel
- **THEN** it is removed and the modal returns to its prior layout

### Requirement: Unavailable startup content degrades gracefully
When none of the startup content can be read from a session's transcript, the breakdown SHALL still show the growth rows and the remainder row, and the startup categories SHALL be absent. A failure to build the breakdown SHALL NOT affect the rest of the detail view.

#### Scenario: No startup content recorded
- **WHEN** a transcript records no memory, skill, agent or MCP content
- **THEN** the breakdown shows the growth rows and a remainder row holding the rest of the context size, and the rest of the detail view renders normally
