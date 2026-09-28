## ADDED Requirements

### Requirement: Selecting a project shows charts for that project
On the Projects page, selecting a project SHALL show, under the list, charts covering that project's
sessions only: a chart of session counts by git branch, a chart of messages and cost by git branch,
and a chart of activity by hour of day. The selection SHALL be reflected in the address so that
reloading or sharing the link reopens the same project's charts, and selecting a different project
SHALL replace the charts. A session SHALL belong to a project by the folder Claude Code files its
transcript under, not by the project's display name, so two projects whose folders share a name are
never combined.

The charts SHALL offer the same time ranges as the Overview page (All time, Today, Yesterday, Past
week, Past month, Past quarter, and Past year), defaulting to All time, and SHALL place sessions in a
range by the same rules. The range SHALL reset to All time when a different project is selected.
Every chart in the panel SHALL reflect only the selected project and range.

The branch charts SHALL show the seven branches with the most sessions individually and fold every
other branch into a single "Other" entry, SHALL give a branch the same color in both charts, and
SHALL show a session with no recorded branch as "(no branch)". A session SHALL be counted under the
branch recorded last in its transcript. The messages-and-cost chart SHALL follow the same rule as the
Overview bar charts: each measure as a percentage of its own peak on one shared axis, with a caption
saying so. The hourly chart SHALL follow the Overview hourly chart, but for the selected project's
sessions only.

#### Scenario: Selecting a project
- **WHEN** the user selects a project on the Projects page
- **THEN** a sessions-by-branch chart, a messages-and-cost-by-branch chart, and an activity-by-hour
  chart for that project are shown under the list, with the time range set to All time

#### Scenario: Only that project's sessions
- **WHEN** project A has two sessions and project B has five
- **THEN** with project A selected, the charts account for those two sessions and none of B's

#### Scenario: Same-named folders are not merged
- **WHEN** two projects at different paths both have the folder name `app`
- **THEN** selecting one shows only the sessions filed under that project's own folder

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
- **WHEN** the selected project's sessions span ten branches
- **THEN** the branch charts show the seven with the most sessions plus one "Other" entry covering
  the remaining three

#### Scenario: Session with no branch
- **WHEN** a session in the selected project has no recorded branch
- **THEN** it is counted under "(no branch)"

#### Scenario: Empty range
- **WHEN** the selected project has no session in the selected range
- **THEN** the panel says no sessions were found for that range instead of showing empty charts

## MODIFIED Requirements

### Requirement: Projects page lists and deletes projects
The Projects page SHALL list every project Claude Code has been run or trusted in, with its name,
path, trust status, last session ID, CLI version, last cost, last start time, lines added and
removed, and MCP servers. Selecting a project in the list SHALL show its charts (see "Selecting a
project shows charts for that project") and SHALL NOT delete or begin deleting anything. The selected
project's panel SHALL offer a "Delete project" control; activating it SHALL open a confirmation
modal that names the project path and says the action cannot be undone, with a control to confirm
and a control to cancel. Deleting SHALL remove the project's entry from Claude Code's configuration
and the project's stored session transcripts, and the project and its sessions SHALL no longer appear
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
