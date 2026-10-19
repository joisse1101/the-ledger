## ADDED Requirements

### Requirement: Rows show a compact-state dot
Each session row SHALL show a dot to the left of the row's content, coloured by the session's compact grade, using the same grade the Live sessions list uses: green for `ok`, amber for `should` and red for `needs`. The dot SHALL be drawn at full opacity regardless of the widget's transparency setting. When the session's status is `idle`, the dot SHALL be drawn as a hollow ring in the same colour instead of a filled dot. A session with no grade SHALL show no dot but keep its row aligned with the other rows. The dot SHALL carry no text, and clicking the row SHALL behave as before.

#### Scenario: Fresh session
- **WHEN** a live session is graded `ok`
- **THEN** its row shows a filled green dot at its left

#### Scenario: Should compact
- **WHEN** a live session is graded `should`
- **THEN** its row shows a filled amber dot at its left

#### Scenario: Needs compact
- **WHEN** a live session is graded `needs`
- **THEN** its row shows a filled red dot at its left

#### Scenario: Idle session
- **WHEN** a session graded `needs` has status `idle`
- **THEN** its dot is a hollow red ring

#### Scenario: Same grade as the Live list
- **WHEN** the Live sessions list shows a "Should compact" pill for a session
- **THEN** that session's widget dot is amber at the same moment

#### Scenario: No grade
- **WHEN** a session has no grade
- **THEN** its row shows no dot and its name stays aligned with the other rows

### Requirement: Row tints follow the widget's transparency setting
The highlight colours that tint a row (a waiting prompt, a finished session, an error status) SHALL follow the widget's transparency setting in the same way the widget's background does, while the row's text and the compact-state dot stay fully opaque.

#### Scenario: Transparent widget
- **WHEN** the widget's transparency is set low and a row is tinted
- **THEN** the tint is as see-through as the widget's background, the row's text is fully readable, and the dot is fully opaque

#### Scenario: Solid widget
- **WHEN** the widget is fully opaque
- **THEN** tinted rows look the same as before
