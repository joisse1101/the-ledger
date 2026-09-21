## MODIFIED Requirements

### Requirement: Live table shows each session's current context size
The Live sessions list SHALL include, for each live session, a Context cell showing the size of that session's context in tokens. In the table layout the Context cell is a column; in the card layout used on narrow screens it is a labelled field on the session's card. Sizes SHALL be humanised: an exact number below 1,000, the nearest thousand with a `k` suffix from 1,000 up to but below 1,000,000, and one decimal with an `M` suffix at 1,000,000 and above.

#### Scenario: Session with responses shows its context size
- **WHEN** a live session has completed at least one response from Claude
- **THEN** its row's or card's Context cell shows the session's current context size, for example `394k`

#### Scenario: Size is humanised
- **WHEN** a session's context size is 742, 80,618, or 1,234,567 tokens
- **THEN** its Context cell shows `742`, `81k`, or `1.2M` respectively

### Requirement: Only absolute token counts are shown
The Context cell and the detail view SHALL express usage only as token counts. They SHALL NOT display a percentage of a context window, a context-window size, or a compaction threshold.

#### Scenario: No percentage or limit
- **WHEN** the Context cell or the detail view is displayed for any session
- **THEN** no value is presented as a percentage of a limit, and no limit or threshold is shown

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
