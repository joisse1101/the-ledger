## ADDED Requirements

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

## MODIFIED Requirements

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
