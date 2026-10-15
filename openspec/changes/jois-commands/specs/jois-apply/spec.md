## ADDED Requirements

### Requirement: Apply runs on the main thread without commit pauses
`/jois:apply` SHALL implement the tasks of an OpenSpec change in the user's own session, showing
each task as it is worked, and SHALL NOT end its turn to wait for a commit confirmation. It SHALL
select the change, read the context files and mark each task done, as `/opsx:apply` does.

#### Scenario: Runs through several concerns in one go
- **WHEN** the user runs `/jois:apply` on a change whose tasks form three concerns
- **THEN** the command SHALL implement and commit all three in sequence without asking for a confirmation word

#### Scenario: Progress is visible
- **WHEN** the command starts a task
- **THEN** it SHALL print which task it is working on before changing files

### Requirement: Commits are made per concern after green checks
After each completed concern, `/jois:apply` SHALL run the project's tests and build. Only when they
pass SHALL it stage the concern's files by explicit path, review the staged diff and commit with a
`type(scope): subject` message that follows the commit-hygiene rule, ending with the attribution
line given for the session. A concern that exceeds the size limits of the commit-hygiene rule SHALL
be split into separate commits first. It SHALL NOT use `git add .`, `git add -A` or `git commit -a`.

#### Scenario: Green checks lead to a commit
- **WHEN** a concern is complete and the tests and build pass
- **THEN** the command SHALL stage only that concern's files by path and commit them

#### Scenario: Red checks block the commit
- **WHEN** the tests or build fail after a concern
- **THEN** the command SHALL NOT commit, SHALL report the failure and SHALL stop, unless the next change is the fix for that failure

#### Scenario: Oversized stage is split
- **WHEN** the finished work spans several concerns
- **THEN** the command SHALL commit them as separate commits, one concern each

### Requirement: Commit authority is limited to the run
`/jois:apply` SHALL commit only on the current branch, SHALL NOT run `git push`, `git commit
--amend`, `git reset`, `git rebase` or any forced operation, and SHALL NOT commit after its run has
ended. If started on the default branch, it SHALL create and switch to a new branch before its first
commit and name that branch in its report.

#### Scenario: Started on main
- **WHEN** the command is run while `main` is checked out
- **THEN** it SHALL create a branch before the first commit and commit there

#### Scenario: No push
- **WHEN** every task is complete
- **THEN** the command SHALL leave the commits local and SHALL NOT push

#### Scenario: Authority ends with the run
- **WHEN** the run has finished and the user later asks for another commit
- **THEN** the commit-hygiene confirmation word SHALL apply again

### Requirement: Apply stops on conditions that need the user
`/jois:apply` SHALL stop, report what it found and wait when a task is ambiguous, when completing a
task needs work beyond the spec, when implementation reveals a design flaw, when tests or build
fail, when it hits a blocker, or when the user interrupts. It SHALL NOT guess through these.

#### Scenario: Ambiguous task
- **WHEN** a task has two plausible readings
- **THEN** the command SHALL stop and ask rather than pick one

#### Scenario: Scope beyond the spec
- **WHEN** a task can only be finished by adding behavior the spec does not describe
- **THEN** the command SHALL surface the added scope and stop

### Requirement: Apply ends with a report of its commits
When `/jois:apply` finishes or stops, it SHALL print the branch, each commit it made as a short
hash and its message, the tasks completed out of the total, and the reason it stopped if it did.

#### Scenario: Finished run
- **WHEN** all tasks are done
- **THEN** the report SHALL list every commit made in the run and suggest archiving the change

#### Scenario: Stopped run
- **WHEN** the run stops on red tests after two commits
- **THEN** the report SHALL list those two commits, the failing check and the task that was in progress

### Requirement: Apply is documented with opt-in guard rails
`toolkit/README.md` SHALL give an opt-in `settings.json` snippet whose `permissions.deny` blocks
`git push*`, and a second snippet whose `permissions.allow` covers `git add`, `git commit`, the
test and build commands and `openspec`, so an unattended run does not stall on prompts. The
installer SHALL NOT write either snippet.

#### Scenario: Hard push block available
- **WHEN** a reader follows the README snippet
- **THEN** a `git push` attempted during a run SHALL be denied by the tool's permissions and not only discouraged by the command text
