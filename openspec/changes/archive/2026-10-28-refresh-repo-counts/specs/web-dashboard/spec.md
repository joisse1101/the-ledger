# Spec Delta

## MODIFIED Requirements

### Requirement: Data refresh is manual and automatic
The app SHALL provide a single refresh control, present on every page, that rescans Claude Code's files, re-reads each project's open issue and pull request counts, and updates all pages, and SHALL show when the data was last refreshed. The control SHALL show it is working until the rescan and the count re-read have finished, and a count that cannot be read SHALL NOT make the refresh fail. It SHALL also rescan automatically every 10 minutes for as long as the server runs, whether or not any browser is connected. The Live list is not affected by this cycle and continues to read the live registry directly.

#### Scenario: Manual refresh
- **WHEN** the user activates the refresh control
- **THEN** all pages show data from a fresh scan and the last-refreshed time is updated

#### Scenario: Manual refresh updates issue and PR counts
- **WHEN** the user activates the refresh control while the Projects page is open and a project's open issue count has changed on its host since the page loaded
- **THEN** the control shows it is working until the counts have been read again, and the project's row then shows the new count

#### Scenario: Counts cannot be read during a refresh
- **WHEN** the user activates the refresh control and the GitHub CLI is missing, signed out, offline or rate-limited
- **THEN** the session data is still refreshed, the last-refreshed time is updated, the control does not report a failure, and the affected Issues and PRs cells show `--`

#### Scenario: Refresh from a page that does not show counts
- **WHEN** the user activates the refresh control on a page other than Projects
- **THEN** the control finishes once the rescan has finished, and the counts are read fresh the next time the Projects page is opened

#### Scenario: Automatic refresh
- **WHEN** 10 minutes have passed since the last scan
- **THEN** the data is rescanned without user action
