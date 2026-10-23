## ADDED Requirements

### Requirement: Worktree is retained with each preserved session
The durable store SHALL record, for every session it holds, the name of the Claude Code worktree the
session ran in (empty when it did not run in one) and the project that worktree belongs to, so a
session keeps its worktree and project attribution after its transcript file is pruned from disk.

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

## MODIFIED Requirements

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
