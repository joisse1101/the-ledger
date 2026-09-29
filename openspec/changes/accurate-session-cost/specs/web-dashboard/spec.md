## MODIFIED Requirements

### Requirement: Overview shows summary figures
The Overview page SHALL show, for the selected range: the number of projects, sessions, and
messages; the average messages per session; the average, longest, shortest, and total session
duration; and the average, most expensive, cheapest, and total session cost. The longest, shortest,
most expensive, and cheapest figures SHALL each let the user find out which project and session ID
they belong to, by hover on a pointer device and by tap on a touch device. Cost figures SHALL be
shown in dollars with two decimals. When the most-expensive or cheapest figure names a session whose
own cost is a best-effort estimate rather than an exact, Claude-Code-reported figure (see "All
sessions list searches, filters, and sorts"), that figure SHALL be marked with an asterisk and a
tooltip explaining that it is an estimate.

#### Scenario: Extremes name their session
- **WHEN** the user hovers or taps the longest-session figure
- **THEN** the project name and session ID of that session are shown

#### Scenario: Costs are estimates in dollars
- **WHEN** the summary figures are shown
- **THEN** cost figures are shown in dollars with two decimals

#### Scenario: An extreme figure from an estimated session
- **WHEN** the most-expensive or cheapest figure names a session whose own cost is an estimate
- **THEN** the figure is marked with an asterisk and a tooltip explains that the amount is a
  best-effort estimate

### Requirement: All sessions list searches, filters, and sorts
The Sessions page SHALL show an All list of every session transcript on disk or preserved in the
transcript-history capability's durable store after being pruned from disk, with each session's
project, title, session ID, start time, last-updated time, message count, cost, context size, CLI
version, and git branch. It SHALL default to newest last-updated first. The user SHALL be able to
search by text contained in the session ID, last message, or first prompt (case-insensitive, matched
literally), filter by one or more projects, versions, and branches, and sort by any column in either
direction, with sessions that have no value for the sort column placed last in both directions.
Filters SHALL combine, so a session must satisfy all of them. The list SHALL be delivered in pages,
with a control to load more, so a large history does not have to be transferred at once. A session
that is also live SHALL be marked as live. Missing values SHALL be shown as `--`.

A session's cost SHALL be either an exact figure Claude Code itself reported for that session or,
when no such figure is available, a best-effort estimate computed from the session's own
recognized-model usage. An estimated cost SHALL be marked with an asterisk and a tooltip explaining
that it is a best-effort figure covering only models this app recognizes and only the session's own
main-thread turns, excluding any subagent spend. When this app's own scan found a specific model it
doesn't recognize, the tooltip SHALL name it (or them, when more than one); otherwise it SHALL explain
whether Claude Code itself flagged the session's own cost as unpriced, or has not yet reported a final
cost for the session at all (still running, or from a build too old to report one). An exact cost
SHALL be shown with no such mark.

#### Scenario: Search matches literally
- **WHEN** the user searches for `a.b`
- **THEN** only sessions containing the literal text `a.b` match, not sessions containing `axb`

#### Scenario: Filters combine
- **WHEN** the user selects project A and branch main
- **THEN** only sessions in project A on branch main are listed

#### Scenario: Missing values sort last
- **WHEN** the user sorts by Context in either direction
- **THEN** sessions with no context value appear after all sessions that have one

#### Scenario: Load more
- **WHEN** more sessions match than one page holds
- **THEN** a page is shown with the total match count and a control that loads the next page

#### Scenario: No matches
- **WHEN** the search and filters match nothing
- **THEN** the list says no sessions match the current filters

#### Scenario: Pruned session still listed
- **WHEN** a session's transcript file has been pruned from disk but a row for it is preserved in
  the transcript-history durable store
- **THEN** the session still appears in the All list using its preserved summary values

#### Scenario: Estimated cost is marked
- **WHEN** a session's cost column shows a best-effort estimate rather than an exact,
  Claude-Code-reported figure
- **THEN** the amount is marked with an asterisk and a tooltip explains what the estimate excludes

#### Scenario: Estimated cost names an unrecognized model
- **WHEN** a session's cost is estimated because this app's own scan found a model its pricing table
  doesn't recognize
- **THEN** the tooltip names that model

#### Scenario: Estimated cost with no named model explains why
- **WHEN** a session's cost is estimated and this app's own scan found no unrecognized model
- **THEN** the tooltip explains whether Claude Code itself flagged the session's cost as unpriced, or
  has not yet reported a final cost for it

#### Scenario: Exact cost is unmarked
- **WHEN** a session's cost column shows Claude Code's own reported cost
- **THEN** the amount is shown with no asterisk

### Requirement: Session detail is available from either list
Selecting a session in the All list SHALL open a detail view for it: a recap (the title, the last
message from Claude, or the first prompt when there is no last message, the start and last-updated
times, the message count, the cost, and the average tokens per message), the token and cache history,
and the "what filled the context" breakdown defined by the live-context-gauge capability. The recap's
cost SHALL follow the same exact-vs-estimate marking as the All list's cost column: an estimate SHALL
be marked with an asterisk and a tooltip explaining what it excludes, and an exact figure SHALL carry
no such mark. If the session's conversation record can't be read, it SHALL say so rather than showing
an empty view. While it is open on a session that is also live, it SHALL update in place as the Live
list refreshes without closing or losing its scroll position. Selecting a session in the **Live
list** instead opens the control view defined by the remote-session-control capability, not this
detail view.

#### Scenario: Open from Live
- **WHEN** the user selects a row in the Live list
- **THEN** the control view defined by the remote-session-control capability opens, not this detail
  view

#### Scenario: Open from All
- **WHEN** the user selects a session in the All list
- **THEN** the detail view opens with the recap above the token history

#### Scenario: Recap marks an estimated cost
- **WHEN** the recap's cost is a best-effort estimate rather than an exact, Claude-Code-reported
  figure
- **THEN** the amount is marked with an asterisk and a tooltip explains what the estimate excludes

#### Scenario: Unreadable record
- **WHEN** the selected session's conversation record can't be read
- **THEN** the detail view says it couldn't read the transcript

#### Scenario: Stays open while live
- **WHEN** the detail view is open on a session (opened from the All list) that is also live, and the
  Live list refreshes
- **THEN** the view stays open, its scroll position is kept, and its numbers update
