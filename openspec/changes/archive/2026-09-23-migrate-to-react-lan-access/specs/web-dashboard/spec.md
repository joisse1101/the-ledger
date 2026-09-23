## Purpose

The Ledger's dashboard as a web app: an Overview of all Claude Code usage, live and historical session lists with a per-session detail view, and a project list, with the ability to delete old sessions and projects. Requirements here capture the behavior the app already had so the move to a web front end can be checked for parity.

## ADDED Requirements

### Requirement: Three pages with persistent navigation
The app SHALL provide three pages, Overview, Sessions, and Projects, reachable from navigation that is present on every page. The app SHALL open on the Sessions page. The current page SHALL be visibly indicated, SHALL be reflected in the address so that reloading or sharing the link returns to the same page, and SHALL survive the browser's back and forward buttons.

#### Scenario: Opening the app
- **WHEN** the user opens the app's root address
- **THEN** the Sessions page is shown and its navigation entry is marked as current

#### Scenario: Reload keeps the page
- **WHEN** the user is on the Projects page and reloads the browser
- **THEN** the Projects page is shown again

#### Scenario: Back button
- **WHEN** the user moves from Sessions to Overview and presses the browser's back button
- **THEN** the Sessions page is shown

### Requirement: Overview can be scoped by a time range
The Overview page SHALL offer the time ranges All time, Today, Yesterday, Past week, Past month, Past quarter, and Past year, defaulting to All time, and every statistic and chart on the page SHALL reflect only the selected range. A session SHALL be placed in a range by the local calendar date it started on (or, when it has no recorded start, the date it was last updated), not by a rolling window of hours. Today SHALL mean sessions that started on today's local date, and Yesterday SHALL mean sessions that started on yesterday's local date only. Past week, month, quarter, and year SHALL run up to and include today.

#### Scenario: Today is a calendar day
- **WHEN** the user selects Today at 00:05
- **THEN** sessions that started since midnight are counted and sessions that started at 23:50 the previous evening are not

#### Scenario: Yesterday excludes today
- **WHEN** the user selects Yesterday
- **THEN** only sessions that started on yesterday's local date are counted

#### Scenario: Empty range
- **WHEN** no session falls in the selected range
- **THEN** the page says no sessions were found for that range instead of showing empty charts

#### Scenario: Range applies everywhere
- **WHEN** the user changes the range
- **THEN** the summary figures, the project chart, and both bar charts all update to the same range

### Requirement: Overview shows summary figures
The Overview page SHALL show, for the selected range: the number of projects, sessions, and messages; the average messages per session; the average, longest, shortest, and total session duration; and the average, most expensive, cheapest, and total session cost. The longest, shortest, most expensive, and cheapest figures SHALL each let the user find out which project and session ID they belong to, by hover on a pointer device and by tap on a touch device.

#### Scenario: Extremes name their session
- **WHEN** the user hovers or taps the longest-session figure
- **THEN** the project name and session ID of that session are shown

#### Scenario: Costs are estimates in dollars
- **WHEN** the summary figures are shown
- **THEN** cost figures are shown in dollars with two decimals

### Requirement: Overview charts break usage down by project and by hour
The Overview page SHALL show a chart of session counts by project, a chart of messages and cost by project, and a chart of activity by hour of day. The project charts SHALL show the seven projects with the most sessions individually and fold every other project into a single "Other" entry. A given project SHALL have the same color in every chart, and "Other" SHALL always use the same neutral color. The hourly chart SHALL bucket sessions by the local hour they started and show only the contiguous range of hours from the first to the last that has activity.

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

### Requirement: Live sessions list updates itself
The Sessions page SHALL show a Live list of the Claude Code sessions currently registered on the machine, with each session's name, title, status, kind, process ID, context, and session ID, and SHALL refresh it automatically about every 2 seconds. It SHALL show when it was last refreshed and offer an Auto-refresh switch, on by default; while the switch is off the list SHALL keep showing its last data. The list SHALL NOT poll while the browser tab is hidden, and SHALL refresh immediately when the tab becomes visible again. When there are no live sessions it SHALL say so.

#### Scenario: A session's status changes
- **WHEN** a live session changes status while the Live list is open with Auto-refresh on
- **THEN** the list shows the new status within a few seconds without user action

#### Scenario: Auto-refresh off
- **WHEN** the user turns Auto-refresh off
- **THEN** the list stops changing and the last-refreshed time stops advancing until it is turned back on

#### Scenario: Hidden tab does not poll
- **WHEN** the browser tab is in the background
- **THEN** no requests for live sessions are made until it is visible again, and one is made as soon as it is

#### Scenario: Nothing running
- **WHEN** no Claude Code session is registered
- **THEN** the Live list shows a message that no sessions were found

### Requirement: All sessions list searches, filters, and sorts
The Sessions page SHALL show an All list of every session transcript on disk, with each session's project, title, session ID, start time, last-updated time, message count, estimated cost, context size, CLI version, and git branch. It SHALL default to newest last-updated first. The user SHALL be able to search by text contained in the session ID, last message, or first prompt (case-insensitive, matched literally), filter by one or more projects, versions, and branches, and sort by any column in either direction, with sessions that have no value for the sort column placed last in both directions. Filters SHALL combine, so a session must satisfy all of them. The list SHALL be delivered in pages, with a control to load more, so a large history does not have to be transferred at once. A session that is also live SHALL be marked as live. Missing values SHALL be shown as `--`.

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

### Requirement: Session detail is available from either list
Selecting a session in the Live list or the All list SHALL open a detail view for it. From the All list it SHALL also show a recap: the title, the last message from Claude (or the first prompt when there is no last message), the start and last-updated times, the message count, the estimated cost, and the average tokens per message. It SHALL show the token and cache history and the "what filled the context" breakdown defined by the live-context-gauge capability. If the session's conversation record can't be read, it SHALL say so rather than showing an empty view. While it is open on a live session, it SHALL update in place as the Live list refreshes without closing or losing its scroll position.

#### Scenario: Open from Live
- **WHEN** the user selects a row in the Live list
- **THEN** the detail view opens with that session's token history

#### Scenario: Open from All
- **WHEN** the user selects a session in the All list
- **THEN** the detail view opens with the recap above the token history

#### Scenario: Unreadable record
- **WHEN** the selected session's conversation record can't be read
- **THEN** the detail view says it couldn't read the transcript

#### Scenario: Stays open while live
- **WHEN** the detail view is open on a live session and the Live list refreshes
- **THEN** the view stays open, its scroll position is kept, and its numbers update

### Requirement: Sessions can be deleted, but not live ones
From the detail view of an All-list session, the user SHALL be able to delete that session's transcript after an explicit confirmation step that says the action cannot be undone. After deletion the session SHALL disappear from the All list without a manual refresh. A session that is currently live SHALL NOT be deletable: the delete control SHALL be replaced by a note saying so, and the server SHALL refuse a delete request for a live session even if it is made directly.

#### Scenario: Confirmed delete
- **WHEN** the user chooses delete on a non-live session and confirms
- **THEN** the transcript is removed from disk and the session no longer appears in the All list

#### Scenario: Cancelled delete
- **WHEN** the user chooses delete and then cancels
- **THEN** nothing is deleted

#### Scenario: Live session
- **WHEN** the user opens the detail view of a session that is also live
- **THEN** there is no delete control and a note says a live session can't be deleted

#### Scenario: Direct request for a live session
- **WHEN** a delete request is made for a live session's ID without going through the UI
- **THEN** the server refuses it and the transcript is left in place

### Requirement: Projects page lists and deletes projects
The Projects page SHALL list every project Claude Code has been run or trusted in, with its name, path, trust status, last session ID, CLI version, last cost, last start time, lines added and removed, and MCP servers. The user SHALL be able to delete a project after an explicit confirmation step that names the project path and says the action cannot be undone. Deleting SHALL remove the project's entry from Claude Code's configuration and the project's stored session transcripts, and the project and its sessions SHALL no longer appear in the app afterwards.

#### Scenario: Confirmed project delete
- **WHEN** the user deletes a project and confirms
- **THEN** its configuration entry and stored transcripts are removed and it no longer appears on the Projects page or in the All sessions list

#### Scenario: Confirmation names the project
- **WHEN** the user starts deleting a project
- **THEN** the confirmation shows that project's path

#### Scenario: No projects
- **WHEN** Claude Code has no projects recorded
- **THEN** the page says no projects were found

### Requirement: Data refresh is manual and automatic
The app SHALL provide a single refresh control, present on every page, that rescans Claude Code's files and updates all pages, and SHALL show when the data was last refreshed. It SHALL also rescan automatically every 10 minutes for as long as the server runs, whether or not any browser is connected. The Live list is not affected by this cycle and continues to read the live registry directly.

#### Scenario: Manual refresh
- **WHEN** the user activates the refresh control
- **THEN** all pages show data from a fresh scan and the last-refreshed time is updated

#### Scenario: Automatic refresh
- **WHEN** 10 minutes have passed since the last scan
- **THEN** the data is rescanned without user action

### Requirement: Theme is chosen per device
The app SHALL support a light and a dark theme, SHALL default to the device's own light or dark preference, and SHALL offer a toggle to override it. The choice SHALL apply only to the device that made it and be remembered by that device's browser. Charts SHALL follow the active theme.

#### Scenario: Follows the device
- **WHEN** a device with no saved choice opens the app while its system is set to dark
- **THEN** the dark theme is shown

#### Scenario: Devices are independent
- **WHEN** the user switches to the light theme on a laptop while a phone has the app open in dark
- **THEN** the phone stays dark

### Requirement: Server problems are shown, not hidden
When the app can't reach the server, or the server reports an error, the affected view SHALL keep showing its last data (if any) and SHALL show that the data may be out of date, with a way to retry. Polling SHALL resume by itself once the server is reachable again.

#### Scenario: Server goes away
- **WHEN** the server stops while the Live list is open
- **THEN** the list keeps its last rows, shows that it can't reach the server, and recovers on its own when the server is back
