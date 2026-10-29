## RENAMED Requirements

- FROM: `### Requirement: Hovering the Ledger button shows Remote mode status and the sign-in code`
- TO: `### Requirement: Hovering the Remote button shows Remote mode status and the sign-in code`

## MODIFIED Requirements

### Requirement: Hovering the Remote button shows Remote mode status and the sign-in code
While Remote mode is starting, ready, or failed, hovering the widget's Remote button SHALL show a
small tooltip window next to the widget, without resizing the widget and without taking focus. It
SHALL show a message for the current step while starting, such as starting Docker or starting the
gateway, and the reason when failed. When ready it SHALL show the scannable sign-in code on an
opaque background that does not follow the widget's transparency setting, the gateway's address
under it without the token, and the time left. It SHALL hide when the pointer leaves, and SHALL
appear by itself for a few seconds when Remote mode becomes ready. While Remote mode is off,
hovering the Remote button SHALL show no code. Hovering the Ledger button SHALL NOT show Remote
mode status or the sign-in code.

#### Scenario: Hover while ready
- **WHEN** Remote mode is ready and the user hovers the Remote button
- **THEN** the tooltip shows the scannable code, the address under it without the token, and the
  time left, and it disappears when the pointer leaves

#### Scenario: Hover while starting
- **WHEN** Remote mode is starting and the user hovers the Remote button
- **THEN** the tooltip shows what is being started, and no code

#### Scenario: Appears on ready
- **WHEN** Remote mode becomes ready
- **THEN** the tooltip appears by itself for a few seconds so the code can be scanned, then hides

#### Scenario: Off
- **WHEN** Remote mode is off and the user hovers the Remote button
- **THEN** no code is shown

#### Scenario: Ledger button does not show the code
- **WHEN** Remote mode is ready and the user hovers the Ledger button
- **THEN** the sign-in code is not shown

#### Scenario: Transparent widget
- **WHEN** the widget's transparency is set low
- **THEN** the code is still drawn on an opaque background and stays scannable

## ADDED Requirements

### Requirement: Hovering the Ledger button shows the projects' open issues and pull requests
Hovering the widget's Ledger button SHALL show a tooltip window next to the widget, without resizing
the widget and without taking focus, listing the projects hosted on GitHub. Each row SHALL show the
project's name, its source (GitHub), its open issue count and its open pull request count, with `--`
for a count that is unavailable. Projects SHALL be ordered by open issues plus open pull requests,
most first, a project with unavailable counts after those with counts, and ties in the order the
backend lists them. At most the configured number of projects SHALL be shown (5 unless set
otherwise), followed by a line giving how many more there are. Projects that are not on GitHub, and
projects that are not git repos, SHALL NOT be listed. The tooltip SHALL hide when the pointer leaves.
It SHALL be shown whatever Remote mode's state, on an opaque background that does not follow the
widget's transparency setting.

#### Scenario: Hover shows the top projects
- **WHEN** seven GitHub projects are known, the configured number is 5, and the user hovers the
  Ledger button
- **THEN** the five with the most open issues plus pull requests are listed, each with its name,
  source, issues and pull requests, followed by "+2 more"

#### Scenario: Non-GitHub and non-repo projects are left out
- **WHEN** a project has no git remote, or its remote is not on GitHub
- **THEN** it is not listed

#### Scenario: Unavailable counts
- **WHEN** a GitHub project's counts cannot be read
- **THEN** its row shows `--` for issues and pull requests and is listed after the projects with counts

#### Scenario: No GitHub projects
- **WHEN** no known project is hosted on GitHub and the user hovers the Ledger button
- **THEN** the tooltip says there are no GitHub projects

#### Scenario: Leaves with the pointer
- **WHEN** the pointer leaves the Ledger button
- **THEN** the tooltip hides

#### Scenario: Independent of Remote mode
- **WHEN** Remote mode is off, starting, ready, or failed and the user hovers the Ledger button
- **THEN** the projects list is shown, not Remote status

### Requirement: The projects list is kept current without delaying the hover
The widget SHALL read the projects' repo info and the configured number at startup, about every
minute, and on every hover of the Ledger button, and SHALL NOT wait for a read before showing the
tooltip: a hover shows the last known rows at once, and rows that arrive while the tooltip is open
SHALL replace them in place. Before the first read has finished, the tooltip SHALL say it is
loading. When a read fails, the last known rows SHALL stay shown. When no read has ever succeeded,
the tooltip SHALL say the projects could not be loaded. The widget SHALL NOT ask the backend to
rescan or to drop its caches for this. If the configured number cannot be read, the widget SHALL use 5.

#### Scenario: Hover shows cached rows at once
- **WHEN** the rows were read a minute ago and the user hovers the Ledger button
- **THEN** the tooltip appears with those rows without waiting, and a read starts in the background

#### Scenario: Newer rows replace the shown ones
- **WHEN** a read finishes while the tooltip is open and the counts changed
- **THEN** the tooltip shows the new counts without being closed

#### Scenario: Before the first read
- **WHEN** the user hovers the Ledger button before the first read has finished
- **THEN** the tooltip says the projects are loading

#### Scenario: Backend unreachable
- **WHEN** the backend does not answer
- **THEN** the last known rows stay shown, or the tooltip says the projects could not be loaded if there never were any

#### Scenario: Setting unreadable
- **WHEN** the configured number cannot be read
- **THEN** at most 5 projects are shown
