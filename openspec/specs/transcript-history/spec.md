## Purpose

Preserves session transcript summary data beyond Claude Code's own on-disk retention window, so
historical usage keeps showing in the app after the original session files are pruned from disk.

## Requirements

### Requirement: Durable retention of transcript summaries
The system SHALL retain a summary row for every session transcript it has ever scanned, in a store
that is never deleted by the app's own startup, shutdown, or refresh cycle, keyed by session ID.

#### Scenario: Session pruned from disk
- **WHEN** a session's transcript file is removed from disk (by Claude Code's own cleanup) and a
  subsequent scan runs
- **THEN** the session's previously recorded summary row SHALL remain present in the durable store

### Requirement: Backup runs independent of the app, and is idempotent
The backup SHALL be runnable as a standalone process without the API server running, and SHALL be
safe to run repeatedly without creating duplicate or conflicting rows for the same session.

#### Scenario: Backup runs while the server is stopped
- **WHEN** the backup runs while no Ledger server process is running
- **THEN** it SHALL scan Claude Code's on-disk data directly and update the durable store

#### Scenario: Repeated runs update in place
- **WHEN** the backup runs again for a session it has already recorded
- **THEN** that session's single row SHALL be updated in place rather than duplicated

### Requirement: Live scan takes precedence on merge
When a session's row exists in both the current live scan and the durable store, the app SHALL use
the live scan's values.

#### Scenario: Active session's figures changed since the last backup
- **WHEN** a session is still on disk and its cost or message count has increased since the last
  backup ran
- **THEN** the app's displayed figures for that session SHALL reflect the live values, not the
  values recorded in the durable store

### Requirement: Historical sessions included in reads
The app's statistics and lists SHALL include sessions known only from the durable store (no longer
present on disk) alongside sessions currently on disk, for any time range or view that covers them.

#### Scenario: Pruned session still counted
- **WHEN** a session's transcript file has been pruned from disk but a row for it exists in the
  durable store
- **THEN** it SHALL still be counted in the Overview statistics for the time range containing its
  start date

### Requirement: Deletion purges the durable store too
Deleting a session's transcript, or a project's transcripts, through the app's existing delete
flows SHALL also remove the matching row(s) from the durable store. A project's transcripts include
those of sessions that ran in its Claude Code worktrees.

#### Scenario: Session deleted by the user
- **WHEN** a user deletes a session transcript through the existing delete flow
- **THEN** its row SHALL be removed from both the live snapshot and the durable store, and it SHALL
  NOT reappear on a later read

#### Scenario: Project deleted by the user
- **WHEN** a user deletes a project
- **THEN** every transcript row belonging to that project, including rows for sessions that ran in
  its worktrees, SHALL be removed from the durable store as well as the live snapshot

### Requirement: Scope is transcripts only
The durable store SHALL retain transcript-level data only. Project-level state (derived from
`~/.claude.json`) is out of scope for this capability and is not archived.

#### Scenario: Project entry changes
- **WHEN** a project entry changes or is removed from Claude Code's own configuration
- **THEN** the durable store SHALL NOT retain or restore any prior version of that project's data

### Requirement: Worktree is retained with each preserved session
The durable store SHALL record, for every session it holds, the name of the Claude Code worktree the
session ran in (empty when it did not run in one) and the project that worktree belongs to, so a
session keeps its worktree and project attribution after its transcript file is pruned from disk.
What counts as a worktree is set by the configured worktree folders (see the dashboard-settings
capability).

#### Scenario: Pruned worktree session keeps its attribution
- **WHEN** a session that ran in a Claude Code worktree has been pruned from disk and only its
  durable-store row remains
- **THEN** reads still count it under its worktree and its parent repo's project

#### Scenario: Rows preserved before worktree tracking are corrected
- **WHEN** the app starts against a durable store whose rows for worktree sessions were recorded
  before worktrees were tracked, so they carry the worktree's folder name as their project and no
  worktree
- **THEN** those rows SHALL be corrected from their recorded working directory, whether or not their
  transcript files still exist, and correcting them again SHALL change nothing

### Requirement: Preserved rows follow the configured worktree folders
Whenever the worktree-folder list is saved, and at every start, every durable-store row SHALL be
reconciled with the current list from its recorded working directory, whether or not its transcript
file still exists. A row in a listed folder SHALL gain its worktree and parent repo's project; a row
whose worktree folder is no longer listed SHALL lose its worktree and take its worktree's name as its
project. Reconciling again with an unchanged list SHALL change nothing.

#### Scenario: Pruned row gains a worktree when its folder is added
- **WHEN** `.trees` is added and the durable store holds a pruned session recorded in
  `C:/repos/the-ledger/.trees/fix-nav` with project `fix-nav` and no worktree
- **THEN** the row is updated to worktree `fix-nav` and project `the-ledger`

#### Scenario: Pruned row loses its worktree when its folder is removed
- **WHEN** `.trees` is removed and the durable store holds a pruned session recorded in
  `C:/repos/the-ledger/.trees/fix-nav` with worktree `fix-nav` and project `the-ledger`
- **THEN** the row is updated to no worktree and project `fix-nav`

#### Scenario: Built-in folder rows are never reverted
- **WHEN** the list is saved with any set of user folders
- **THEN** rows recorded in a `.claude/worktrees` folder keep their worktree and parent repo's project

#### Scenario: Reconciling is idempotent
- **WHEN** the rows are reconciled twice with the same list
- **THEN** the second pass changes no row
