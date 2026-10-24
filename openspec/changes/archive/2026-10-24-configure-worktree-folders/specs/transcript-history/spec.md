## MODIFIED Requirements

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

## ADDED Requirements

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
