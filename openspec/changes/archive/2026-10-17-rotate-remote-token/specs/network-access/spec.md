## ADDED Requirements

### Requirement: A new token is issued each time Remote mode turns on
The app SHALL create a new random access token of at least 128 bits every time Remote mode goes from
off to starting, and SHALL keep it only in memory for as long as that Remote session lasts. It SHALL
NOT store the token on disk, SHALL NOT read one from an environment setting, and SHALL NOT reuse a
token from an earlier Remote session or an earlier run of the app. A request to turn Remote mode on
while it is already starting or ready SHALL NOT create another token. The token SHALL be discarded
whenever Remote mode returns to off, whether the user switched it off, its time limit ran out, or
starting it failed. While no token exists, every request from another device SHALL be refused, even
if the gateway is still running.

#### Scenario: Turned on
- **WHEN** Remote mode is switched on from the off state
- **THEN** a token that has never been used before exists before the gateway starts answering

#### Scenario: Turned on again
- **WHEN** Remote mode is switched off and then on again
- **THEN** the second session's token differs from the first session's token

#### Scenario: Already on
- **WHEN** Remote mode is starting or ready and a request to turn it on arrives
- **THEN** the current token and the sign-in code built from it stay the same

#### Scenario: Switched off
- **WHEN** Remote mode is switched off and a device that held the old token requests any data
- **THEN** it is refused as unauthorized

#### Scenario: Time limit reached
- **WHEN** Remote mode turns itself off after its time limit
- **THEN** the token is discarded and a device that held it is refused

#### Scenario: Start fails
- **WHEN** Remote mode fails to start
- **THEN** no token remains valid

#### Scenario: Gateway left running
- **WHEN** Remote mode is off but the gateway container could not be stopped, and a device on the
  network requests data
- **THEN** it is refused as unauthorized

#### Scenario: Backend restarted
- **WHEN** the backend is restarted
- **THEN** Remote mode is off and no token exists until Remote mode is turned on

#### Scenario: Token is not stored
- **WHEN** Remote mode has been turned on and the project and the machine's app files are inspected
- **THEN** the token appears in no file

## MODIFIED Requirements

### Requirement: Opening a link once signs the device in
Opening the app's address with the token attached SHALL sign that browser in: the browser SHALL be remembered so later visits to the plain address work without the token, and the token SHALL be removed from the address bar and browser history entry so it is not left visible or copied along with the page address. A device that is signed in SHALL stay signed in until the token it holds is no longer the current one, which happens whenever Remote mode is turned off. Opening the address with a wrong token SHALL NOT sign the device in. A signed-in device whose token is no longer current SHALL be told it is not signed in until it opens a link carrying the new token.

#### Scenario: First visit from a phone
- **WHEN** the user scans the sign-in code on a phone
- **THEN** the dashboard loads and the address shown in the browser no longer contains the token

#### Scenario: Later visit
- **WHEN** that phone later opens the plain address without the token while the same Remote session is still on
- **THEN** the dashboard loads

#### Scenario: Token replaced
- **WHEN** Remote mode is switched off and on again, so the server's token is replaced, and a phone
  signed in with the old token opens the plain address
- **THEN** it is shown that the device isn't signed in, until it scans the new sign-in code

### Requirement: Startup tells the user how to open the app
When the app's backend starts it SHALL print the address of the app's frontend to open on the
machine itself, and note that the frontend must be running for that address to answer. Starting the
gateway SHALL NOT print an address or code that signs a device in; the only place a sign-in address
or code is shown is the dashboard, to the machine running the app, while Remote mode is ready. If the
web interface has not been built, starting the frontend SHALL say clearly that it is missing and how
to build it, and SHALL NOT serve a broken page.

#### Scenario: Backend start output
- **WHEN** the backend starts
- **THEN** it prints the frontend address for the local machine and no access token

#### Scenario: Network start output
- **WHEN** the gateway is started from a command line
- **THEN** nothing printed contains an access token or a sign-in code, and the output does not offer
  a link that signs a device in

#### Scenario: Interface not built
- **WHEN** the frontend is started before the web interface has been built
- **THEN** it says clearly that the interface is missing and gives the command that builds it,
  instead of serving a broken page

### Requirement: The sign-in code is available to the local machine as an image
While Remote mode is ready, the app SHALL offer the machine running it the gateway's sign-in code
as an image, together with the gateway's address for display and the time left until Remote mode
turns itself off. The code SHALL encode the full HTTPS sign-in address for the machine's first
network address, including the token created for this Remote session. The display address SHALL be the
HTTPS address and port only, never the token. Because the code contains the access token, it SHALL be
refused for any request that is not from the machine running the app, even with a valid token. While
Remote mode is off or not yet ready there SHALL be no code.

#### Scenario: Local request while ready
- **WHEN** Remote mode is ready and the machine running the app asks for the sign-in code
- **THEN** it receives a scannable image of the full sign-in address, the address without the
  token, and the time left

#### Scenario: Code matches the session
- **WHEN** Remote mode is switched off and on again and the code is requested each time
- **THEN** the two codes differ, and only the second one signs a device in

#### Scenario: Other device asks
- **WHEN** a device on the network asks for the sign-in code and presents the correct access token
- **THEN** it is refused and no code or token is revealed

#### Scenario: Not ready
- **WHEN** Remote mode is off, starting, or failed and the machine running the app asks for the code
- **THEN** no code is returned and the response says Remote mode is not ready

## REMOVED Requirements

### Requirement: Token is set once and stays valid across restarts
**Reason**: A token that never changes outlives the Remote session it was shared for. Each Remote session now has its own token (see "A new token is issued each time Remote mode turns on").
**Migration**: Nothing to migrate. The backend no longer reads `api/.ledger/token` or `LEDGER_TOKEN`.
