## MODIFIED Requirements

### Requirement: All sessions list searches, filters, and sorts
The Sessions page SHALL show an All list of every session transcript on disk or preserved in the transcript-history capability's durable store after being pruned from disk, with each session's project, title, session ID, start time, last-updated time, message count, estimated cost, context size, CLI version, and git branch. It SHALL default to newest last-updated first. The user SHALL be able to search by text contained in the session ID, last message, or first prompt (case-insensitive, matched literally), filter by one or more projects, versions, and branches, and sort by any column in either direction, with sessions that have no value for the sort column placed last in both directions. Filters SHALL combine, so a session must satisfy all of them. The list SHALL be delivered in pages, with a control to load more, so a large history does not have to be transferred at once. A session that is also live SHALL be marked as live. Missing values SHALL be shown as `--`.

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
- **WHEN** a session's transcript file has been pruned from disk but a row for it is preserved in the transcript-history durable store
- **THEN** the session still appears in the All list using its preserved summary values
