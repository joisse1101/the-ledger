## MODIFIED Requirements

### Requirement: One-click startup brings up only what the widget needs
A start script SHALL start the backend with no visible console window, only if it is not already running, and then launch the widget. It SHALL NOT start the frontend or the gateway container. Before launching it SHALL check that the widget's packages and Electron binary are actually present and current, install or rebuild them when they are not, and stop with an error when that fails. It SHALL use the same backend and frontend ports as the main start command. The project SHALL provide a way to create a desktop shortcut that runs it, and a way to enable and disable running it at logon.

#### Scenario: Cold start from the shortcut
- **WHEN** nothing is running and the user runs the desktop shortcut
- **THEN** the backend and the widget are running, with no console window left open, and neither the frontend nor the gateway is running

#### Scenario: Backend already running
- **WHEN** the backend is already running and the user runs the shortcut
- **THEN** only the widget is started, and no second backend is started

#### Scenario: Widget dependencies empty or incomplete
- **WHEN** the widget's packages folder exists but is empty, or the Electron binary is missing, and the user runs the shortcut
- **THEN** the missing pieces are installed first and the widget then starts

#### Scenario: Same ports as the main start
- **WHEN** the main start command has chosen and saved the backend port and the user runs the shortcut
- **THEN** the widget uses that port

#### Scenario: Logon autostart
- **WHEN** logon autostart is enabled and the user signs in
- **THEN** the backend and widget start without further action

#### Scenario: Autostart disabled
- **WHEN** the user disables logon autostart
- **THEN** nothing starts at the next sign-in, and the desktop shortcut keeps working
