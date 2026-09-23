# responsive-layout Specification

## Purpose

Makes the dashboard usable on any screen from a phone to a wide monitor, so the same pages can be checked from a phone on the same network without pinching, horizontal scrolling, or cut-off content.

## Requirements

### Requirement: Layout adapts to three width classes
The app SHALL adapt its layout to the viewport width in three classes: narrow (under 640 px), medium (640 to 1023 px), and wide (1024 px and above). The layout SHALL change when the viewport crosses a class boundary, including when a phone is rotated or a desktop window is resized, without a page reload and without losing the current page, filters, or open detail view.

#### Scenario: Rotating a phone
- **WHEN** a phone showing the Sessions page in portrait is rotated to landscape
- **THEN** the layout switches to the class for the new width and the page, search text, filters, and any open detail view are unchanged

#### Scenario: Resizing a desktop window
- **WHEN** a desktop browser window is narrowed below 640 px
- **THEN** the narrow layout is shown

### Requirement: No horizontal page scrolling
At every viewport width from 320 px upward, the page SHALL NOT require horizontal scrolling to reach any content, and no text, control, or chart SHALL be clipped by the screen edge. Content that is inherently wide, such as a data table inside the detail view, MAY scroll horizontally within its own container but SHALL NOT widen the page.

#### Scenario: Smallest supported phone
- **WHEN** any page is shown at 320 px wide
- **THEN** the page has no horizontal scrollbar and every control is fully visible

#### Scenario: Wide table in detail view
- **WHEN** the detail view's all-responses table is wider than the screen
- **THEN** the table scrolls sideways inside its own container while the rest of the page stays fixed

### Requirement: Session and project lists become cards on narrow screens
On narrow viewports the Live sessions, All sessions, and Projects lists SHALL be shown as a vertical stack of cards, one per item, each showing that item's most important fields (for a session: project, title or name, status or last-updated time, and context or cost) with the remaining fields available by opening the item. On medium viewports they SHALL be shown as tables that omit the lowest-priority columns. On wide viewports they SHALL be shown as tables with all columns. In every class an item SHALL be selectable to open its detail, and the same items and order SHALL be shown.

#### Scenario: Phone shows cards
- **WHEN** the Live list is shown at 390 px wide
- **THEN** each live session is a card showing its project, title or name, status, and context, and no table header row is shown

#### Scenario: Desktop shows a table
- **WHEN** the All list is shown at 1280 px wide
- **THEN** every column is shown in a table with sortable headers

#### Scenario: Sorting on a phone
- **WHEN** the All list is in the card layout
- **THEN** the user can still choose the sort column and direction, through a control other than the table headers

#### Scenario: Same data in every layout
- **WHEN** the viewport changes from wide to narrow
- **THEN** the same sessions are listed in the same order, now as cards

### Requirement: Navigation stays reachable on phones
On narrow viewports, navigation between Overview, Sessions, and Projects SHALL be a bar fixed to the bottom of the screen within thumb reach, and the refresh control and theme toggle SHALL remain reachable without horizontal scrolling. On medium and wide viewports navigation SHALL be a top bar. Fixed bars SHALL NOT cover page content or the device's safe areas such as a notch or home indicator.

#### Scenario: Bottom bar on a phone
- **WHEN** any page is shown at 390 px wide
- **THEN** the three page entries are in a bar fixed to the bottom of the screen, and the last item of the page's content can be scrolled fully clear of it

#### Scenario: Top bar on a desktop
- **WHEN** any page is shown at 1280 px wide
- **THEN** the page entries are in a bar at the top

### Requirement: Detail view uses the whole screen on phones
On narrow viewports the session detail view SHALL fill the screen as a sheet with a close control that is always visible, and closing it SHALL return to the list in the same scroll position. On medium and wide viewports it SHALL be a dialog over the page. Its charts and tables SHALL fit the available width.

#### Scenario: Sheet on a phone
- **WHEN** the user taps a session at 390 px wide
- **THEN** the detail view fills the screen and its close control stays visible while its contents scroll

#### Scenario: Closing returns to place
- **WHEN** the user closes the detail view
- **THEN** the list is shown at the scroll position it had before

### Requirement: Overview grids and charts reflow
The Overview page SHALL arrange its summary figures and charts by width class: on narrow viewports, a single column of charts and summary figures in a grid of two per row; on medium viewports, charts in one column and summary figures in a wider grid; on wide viewports, the project chart beside the summary figures with the bar charts full width below. Charts SHALL size themselves to their container width and SHALL remain legible (labels not overlapping or clipped, legends visible) at 320 px wide. The time-range selector SHALL remain usable on narrow viewports, by wrapping or scrolling within itself.

#### Scenario: Charts fit a phone
- **WHEN** the Overview page is shown at 360 px wide
- **THEN** each chart fills the width of the screen, its axis labels and legend are not clipped, and the page has no horizontal scrollbar

#### Scenario: Time range on a phone
- **WHEN** the Overview page is shown at 360 px wide
- **THEN** all seven time ranges can be reached without the page scrolling sideways

#### Scenario: Wide layout
- **WHEN** the Overview page is shown at 1280 px wide
- **THEN** the session-count chart sits beside the summary figures and the two bar charts span the full width below

### Requirement: Touch-friendly controls
On touch devices every interactive control SHALL have a tap target of at least 44 by 44 CSS pixels, and adjacent controls SHALL be spaced so that a tap does not land on the wrong one. Nothing SHALL be available only on hover: any information shown in a hover tooltip on a pointer device SHALL also be available by tap. The page SHALL NOT be zoomed by the browser when a text field is focused.

#### Scenario: Tap targets
- **WHEN** the navigation, refresh control, and list items are shown on a phone
- **THEN** each is at least 44 by 44 CSS pixels

#### Scenario: Tooltip content on touch
- **WHEN** a touch user taps the longest-session figure on the Overview page
- **THEN** the project and session ID that a pointer user would see on hover are shown

#### Scenario: Focusing search
- **WHEN** a phone user taps the search field
- **THEN** the page does not zoom in
