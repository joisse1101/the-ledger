## Purpose

Starts and stops the whole app from one command: it makes sure everything the app needs is in place, brings up the backend, frontend and desktop widget, and confirms each one works instead of leaving the user with a silent failure.

## ADDED Requirements

### Requirement: One start command brings up the backend, frontend and widget
The start command SHALL start the backend, the frontend and the desktop widget, in that order, and SHALL start the widget only once the backend answers. It SHALL accept a switch that skips the widget. The widget SHALL NOT start a second backend when the start command has already started one.

#### Scenario: Default start
- **WHEN** the user runs the start command with nothing running
- **THEN** the backend, the frontend and the widget are running, and the widget shows data from the backend the start command started

#### Scenario: Widget skipped
- **WHEN** the user runs the start command with the widget switch off
- **THEN** the backend and the frontend start and no widget is launched

#### Scenario: Widget already running
- **WHEN** the widget is already running and the user runs the start command
- **THEN** no second widget appears and the existing one is left running

### Requirement: Missing prerequisites stop the start with a pointer to install them
The start command SHALL check that Python and Node are installed before starting anything, and Docker only when Remote mode is requested. When one is missing it SHALL name it, print the official page to install it from, start nothing, and exit with a failure code.

#### Scenario: Node is missing
- **WHEN** Node is not installed and the user runs the start command
- **THEN** it says Node is missing, prints where to download it, starts nothing, and exits with a failure code

#### Scenario: Docker is missing without Remote mode
- **WHEN** Docker is not installed and the user starts without requesting Remote mode
- **THEN** the start continues normally

#### Scenario: Docker is missing with Remote mode
- **WHEN** Docker is not installed and the user starts with Remote mode requested
- **THEN** it says Docker is missing, prints where to download it, starts nothing, and exits with a failure code

### Requirement: Missing or incomplete dependencies are repaired before starting
The start command SHALL check that the backend's Python environment and requirements, the frontend's packages, the widget's packages and the widget's Electron binary are actually present and match their lock or requirements files, not merely that their folders exist. It SHALL install or rebuild whatever is missing or out of date, say what it is doing, and stop with a clear error when a repair fails.

#### Scenario: Empty folders
- **WHEN** the backend's environment folder and the widget's packages folder exist but are empty
- **THEN** the start command rebuilds them before starting anything

#### Scenario: Electron binary missing
- **WHEN** the widget's packages are installed but the Electron binary is missing
- **THEN** the start command fetches the binary before launching the widget

#### Scenario: Everything current
- **WHEN** every dependency is present and current
- **THEN** the start command installs nothing

#### Scenario: Repair fails
- **WHEN** a dependency cannot be installed, for example because there is no network
- **THEN** the start command names what failed, starts nothing, and exits with a failure code

### Requirement: Ports are chosen from a range and stay the same between runs
Each of the backend, frontend and gateway SHALL get its port from the first of these that applies: an explicit parameter, a value in the repo's `.env`, the port saved from an earlier run, or the first free port in 8501-8599. A port chosen by scanning SHALL be saved so later runs, the widget and the install scripts use the same one. When a saved port is in use, it SHALL be reused if what holds it is this app's backend, and otherwise a new free port SHALL be chosen and saved.

#### Scenario: First run
- **WHEN** no port is configured or saved and the user starts the app
- **THEN** free ports in 8501-8599 are chosen, saved, and used

#### Scenario: Later run
- **WHEN** the saved ports are free on the next start
- **THEN** the same ports are used again

#### Scenario: Saved port taken by something else
- **WHEN** another program holds a saved port
- **THEN** a different free port in the range is chosen, saved, and used, and the start does not fail because of the conflict

#### Scenario: Saved port held by this app
- **WHEN** a saved port is held by this app's own backend
- **THEN** it is reused and no second backend is started

#### Scenario: Explicit choice wins
- **WHEN** the user passes a port parameter or sets one in `.env`
- **THEN** that port is used instead of the saved one

### Requirement: The start command confirms everything came up
After launching, the start command SHALL check that the backend, the frontend and, unless skipped, the widget are actually running, print each one's address or state, and exit with a failure code when any of them is not.

#### Scenario: All up
- **WHEN** everything starts
- **THEN** the summary lists each piece as running with its address, and the command exits successfully

#### Scenario: Frontend does not come up
- **WHEN** the frontend fails to start
- **THEN** the summary says so and the command exits with a failure code

### Requirement: A relay hook pointing at an old port is offered a reinstall
When the relay hook is installed with a backend port different from the one in use, the start command SHALL tell the user and offer to reinstall the hook. With a console attached it SHALL ask first. With no console, or when told to assume yes, it SHALL reinstall the hook and say that it did.

#### Scenario: Port changed, console attached
- **WHEN** the relay hook is installed for an old backend port and the user starts the app in a console
- **THEN** it asks whether to reinstall the hook and does so only if the user agrees

#### Scenario: Port changed, no console
- **WHEN** the same happens with no console attached
- **THEN** the hook is reinstalled for the current port and the output says so

#### Scenario: Hook not installed
- **WHEN** the relay hook is not installed
- **THEN** the start command does not mention it or install it

### Requirement: Stopping closes the widget the start command launched
The stop command SHALL close the widget when the start command launched it, along with the backend and frontend it already stops. It SHALL NOT close a widget that was already running when the start command ran.

#### Scenario: Widget launched by the start command
- **WHEN** the start command launched the widget and the user runs the stop command
- **THEN** the widget is closed with the backend and frontend

#### Scenario: Widget was already running
- **WHEN** the widget was running before the start command and the user runs the stop command
- **THEN** the widget is left running
