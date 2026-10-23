## MODIFIED Requirements

### Requirement: Overview charts break usage down by project and by hour
The Overview page SHALL show a chart of session counts by project, a chart of messages and cost by project, and a chart of activity by hour of day. The project charts SHALL show the seven projects with the most sessions individually and fold every other project into a single "Other" entry. A given project SHALL have the same color in every chart, and "Other" SHALL always use the same neutral color. A session that ran in a Claude Code worktree SHALL be counted under the project of the repo the worktree belongs to, never as a project of its own, and its figures SHALL be included in that project's. The hourly chart SHALL bucket sessions by the local hour they started and show only the contiguous range of hours from the first to the last that has activity.

Each bar chart that pairs two measures on different scales SHALL express each measure as a percentage of its own peak so both share one axis, and SHALL carry a caption explaining that normalization. It SHALL NOT use two independent value axes.

#### Scenario: Tail of projects is folded
- **WHEN** the selected range has activity in ten projects
- **THEN** the project charts show the seven with the most sessions plus one "Other" entry covering the remaining three

#### Scenario: Project keeps its color
- **WHEN** a project appears in both the session-count chart and the messages-and-cost chart
- **THEN** it is drawn in the same color in each

#### Scenario: Two measures share an axis
- **WHEN** the messages-and-cost chart is shown
- **THEN** each measure is scaled to a percentage of its own peak on one shared axis, and a caption says so

#### Scenario: Quiet hours are trimmed
- **WHEN** all activity started between 9am and 6pm
- **THEN** the hourly chart shows only the hours from 9am to 6pm

#### Scenario: Worktree sessions count toward their repo
- **WHEN** a session ran in the worktree `add-wiki-docs` of the repo `the-ledger`, including one that
  changed directory into a subfolder of that worktree
- **THEN** the project charts count it under `the-ledger`, and no `add-wiki-docs` project is shown

### Requirement: All sessions list searches, filters, and sorts
The Sessions page SHALL show an All list of every session transcript on disk or preserved in the
transcript-history capability's durable store after being pruned from disk, with each session's
project, title, session ID, start time, last-updated time, message count, cost, context size, CLI
version, git branch, and worktree. It SHALL default to newest last-updated first. The user SHALL be able to
search by text contained in the session ID, last message, or first prompt (case-insensitive, matched
literally), filter by one or more projects, versions, branches, and worktrees, and sort by any column in either
direction, with sessions that have no value for the sort column placed last in both directions.
Filters SHALL combine, so a session must satisfy all of them. The list SHALL be delivered in pages,
with a control to load more, so a large history does not have to be transferred at once. A session
that is also live SHALL be marked as live. Missing values SHALL be shown as `--`.

A session's worktree SHALL be the name of the Claude Code worktree it ran in, and SHALL be shown as
`--` for a session that did not run in one. The Worktree filter SHALL offer only worktree names that
at least one session has. A session in a worktree SHALL keep its own git branch in the Branch column.

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

#### Scenario: Filter by worktree
- **WHEN** the user selects the worktree `add-wiki-docs`
- **THEN** only sessions that ran in that worktree are listed, each still showing its own branch

#### Scenario: Session outside a worktree
- **WHEN** a session did not run in a Claude Code worktree
- **THEN** its Worktree column shows `--` and it is not matched by any worktree selection

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

### Requirement: Projects page lists and deletes projects
The Projects page SHALL list every project Claude Code has been run or trusted in, with its name,
path, trust status, last session ID, CLI version, last cost, last start time, lines added and
removed, and MCP servers. Selecting a project in the list SHALL show its charts (see "Selecting a
project shows charts for that project") and SHALL NOT delete or begin deleting anything. The selected
project's panel SHALL offer a "Delete project" control; activating it SHALL open a confirmation
modal that names the project path and says the action cannot be undone, with a control to confirm
and a control to cancel. Deleting SHALL remove the project's entry from Claude Code's configuration
and the project's stored session transcripts, including the transcripts of sessions that ran in the
project's Claude Code worktrees, and the project and its sessions SHALL no longer appear
in the app afterwards; when the deleted project was the selected one, the selection SHALL be cleared.
While a delete is in progress the modal SHALL NOT be dismissible, and if the delete fails the modal
SHALL stay open and show the error. On a device that isn't the machine running the app, the delete
control SHALL NOT be shown, since only a local request can ever delete a project.

#### Scenario: Selecting a row does not delete
- **WHEN** the user selects a project row
- **THEN** its charts are shown and no confirmation or delete action is started

#### Scenario: Confirmed project delete
- **WHEN** the user activates "Delete project" for the selected project and confirms in the modal
- **THEN** its configuration entry and stored transcripts are removed, the modal closes, the
  selection is cleared, and it no longer appears on the Projects page or in the All sessions list

#### Scenario: Worktree sessions are deleted with their project
- **WHEN** the user confirms deleting a project that has sessions recorded in its worktrees
- **THEN** those sessions' transcripts are removed too, and none of them remains in the All sessions
  list

#### Scenario: Confirmation names the project
- **WHEN** the user activates "Delete project"
- **THEN** a modal opens showing that project's path and stating the action cannot be undone

#### Scenario: Cancelled delete
- **WHEN** the confirmation modal is open and the user cancels or dismisses it
- **THEN** nothing is deleted and the project stays selected

#### Scenario: Delete in progress
- **WHEN** a confirmed delete is still in progress
- **THEN** the modal's controls are disabled and it can't be dismissed until the request finishes

#### Scenario: Delete fails
- **WHEN** the server refuses or fails the delete
- **THEN** the modal stays open and shows the error, and the project is left in place

#### Scenario: No projects
- **WHEN** Claude Code has no projects recorded
- **THEN** the page says no projects were found

#### Scenario: Remote device sees no delete control
- **WHEN** the Projects page is open on a device that isn't the machine running the app
- **THEN** there is no delete control for any project, though selecting a project still shows its
  charts

### Requirement: Selecting a project shows charts for that project
On the Projects page, selecting a project SHALL show, under the list, charts covering that project's
sessions only: a chart of session counts by work stream, a chart of messages and cost by work stream,
and a chart of activity by hour of day. The selection SHALL be reflected in the address so that
reloading or sharing the link reopens the same project's charts, and selecting a different project
SHALL replace the charts. A session SHALL belong to a project by the folder Claude Code files its
transcript under, not by the project's display name, so two projects whose folders share a name are
never combined. A session that ran in one of the project's Claude Code worktrees SHALL also belong to
that project, although Claude Code files its transcript under a different folder.

A work stream SHALL be the worktree a session ran in, labelled `wt <name>`, or, for a session that
did not run in a worktree, its git branch. A session in a worktree SHALL be counted under its
worktree for its whole run, even if it switched branches inside it, and a worktree label SHALL never
be merged with a branch of the same name.

The charts SHALL offer the same time ranges as the Overview page (All time, Today, Yesterday, Past
week, Past month, Past quarter, and Past year), defaulting to All time, and SHALL place sessions in a
range by the same rules. The range SHALL reset to All time when a different project is selected.
Every chart in the panel SHALL reflect only the selected project and range.

The work-stream charts SHALL show the seven work streams with the most sessions individually and fold
every other work stream into a single "Other" entry, SHALL give a work stream the same color in both
charts, and SHALL show a session that has neither a worktree nor a recorded branch as "(no branch)".
A session outside a worktree SHALL be counted under the branch recorded last in its transcript. The
messages-and-cost chart SHALL follow the same rule as the
Overview bar charts: each measure as a percentage of its own peak on one shared axis, with a caption
saying so. The hourly chart SHALL follow the Overview hourly chart, but for the selected project's
sessions only, with worktree sessions combined in it rather than split out.

The panel's summary figures SHALL show how many distinct branches and how many distinct worktrees the
selected project's sessions in the selected range cover.

#### Scenario: Selecting a project
- **WHEN** the user selects a project on the Projects page
- **THEN** a sessions-by-work-stream chart, a messages-and-cost-by-work-stream chart, and an
  activity-by-hour chart for that project are shown under the list, with the time range set to All time

#### Scenario: Only that project's sessions
- **WHEN** project A has two sessions and project B has five
- **THEN** with project A selected, the charts account for those two sessions and none of B's

#### Scenario: Same-named folders are not merged
- **WHEN** two projects at different paths both have the folder name `app`
- **THEN** selecting one shows only the sessions filed under that project's own folder

#### Scenario: Worktree sessions appear under their project
- **WHEN** project A has three sessions on its own folder and two sessions that ran in its worktree
  `fix-login`
- **THEN** with project A selected, the charts account for all five sessions, the two worktree
  sessions as the work stream `wt fix-login`

#### Scenario: Worktree supersedes branch
- **WHEN** a session in the worktree `fix-login` recorded the branch `worktree-fix-login`, and
  another session in the main tree recorded the branch `main`
- **THEN** the first is counted under `wt fix-login` and the second under `main`; the first is not
  counted under any branch

#### Scenario: Switching branches inside a worktree
- **WHEN** a session in the worktree `fix-login` switches to the branch `feat/x` and back
- **THEN** it is still counted under `wt fix-login`

#### Scenario: Worktree label does not collide with a branch
- **WHEN** a project has a branch named `fix-login` and a worktree named `fix-login`
- **THEN** the charts show them as two entries, `fix-login` and `wt fix-login`

#### Scenario: Time range applies to every chart
- **WHEN** the user changes the time range with a project selected
- **THEN** all three charts update to the same range

#### Scenario: Range resets on a new project
- **WHEN** the user has Past week selected and then selects a different project
- **THEN** the range returns to All time

#### Scenario: Selection survives a reload
- **WHEN** a project is selected and the user reloads the browser
- **THEN** the same project is selected and its charts are shown again

#### Scenario: Tail of branches is folded
- **WHEN** the selected project's sessions span ten branches and none ran in a worktree
- **THEN** the work-stream charts show the seven with the most sessions plus one "Other" entry
  covering the remaining three

#### Scenario: Tail of work streams is folded
- **WHEN** the selected project's sessions span ten work streams, branches and worktrees together
- **THEN** the work-stream charts show the seven with the most sessions plus one "Other" entry
  covering the remaining three

#### Scenario: Session with no branch
- **WHEN** a session in the selected project has no worktree and no recorded branch
- **THEN** it is counted under "(no branch)"

#### Scenario: Summary counts branches and worktrees
- **WHEN** the selected range covers sessions on two branches and in three worktrees
- **THEN** the summary figures show 2 branches and 3 worktrees

#### Scenario: Empty range
- **WHEN** the selected project has no session in the selected range
- **THEN** the panel says no sessions were found for that range instead of showing empty charts
