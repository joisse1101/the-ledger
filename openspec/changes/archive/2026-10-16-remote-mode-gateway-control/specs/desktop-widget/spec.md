## ADDED Requirements

### Requirement: Widget can turn Remote mode on and off
The widget SHALL have a Remote mode toggle that turns the app's Remote mode on or off through the
backend, with the same effect as the toggle on the Ledger's Live list, including starting what is
needed for other devices to connect and closing it again when turned off. The widget SHALL start
neither the container runtime nor the gateway itself. The toggle SHALL show Remote mode's state
(off, starting, ready, or failed) without needing a hover, and SHALL stay in step with changes made
elsewhere, such as from the Ledger or by the 8 hour expiry.

#### Scenario: Turn on from the widget
- **WHEN** the user turns the widget's Remote mode toggle on while the gateway is stopped
- **THEN** the toggle shows starting, then ready once other devices can connect

#### Scenario: Turn off from the widget
- **WHEN** the user turns the toggle off
- **THEN** Remote mode is off and the gateway is stopped, as if turned off in the Ledger

#### Scenario: Changed elsewhere
- **WHEN** Remote mode is turned on or off in the Ledger, or expires after 8 hours
- **THEN** the widget's toggle shows the new state within a few seconds

#### Scenario: Cannot start
- **WHEN** Remote mode fails to start
- **THEN** the toggle shows failed and the reason is available in the tooltip

### Requirement: Hovering the Ledger button shows Remote mode status and the sign-in code
While Remote mode is starting, ready, or failed, hovering the widget's Ledger button SHALL show a
small tooltip window next to the widget, without resizing the widget and without taking focus. It
SHALL show a message for the current step while starting, such as starting Docker or starting the
gateway, and the reason when failed. When ready it SHALL show the scannable sign-in code on an
opaque background that does not follow the widget's transparency setting, the gateway's address
under it without the token, and the time left. It SHALL hide when the pointer leaves, and SHALL
appear by itself for a few seconds when Remote mode becomes ready. While Remote mode is off,
hovering SHALL show no code.

#### Scenario: Hover while ready
- **WHEN** Remote mode is ready and the user hovers the Ledger button
- **THEN** the tooltip shows the scannable code, the address under it without the token, and the
  time left, and it disappears when the pointer leaves

#### Scenario: Hover while starting
- **WHEN** Remote mode is starting and the user hovers the Ledger button
- **THEN** the tooltip shows what is being started, and no code

#### Scenario: Appears on ready
- **WHEN** Remote mode becomes ready
- **THEN** the tooltip appears by itself for a few seconds so the code can be scanned, then hides

#### Scenario: Off
- **WHEN** Remote mode is off and the user hovers the Ledger button
- **THEN** no code is shown

#### Scenario: Transparent widget
- **WHEN** the widget's transparency is set low
- **THEN** the code is still drawn on an opaque background and stays scannable
