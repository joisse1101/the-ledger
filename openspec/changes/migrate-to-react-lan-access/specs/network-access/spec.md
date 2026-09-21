## Purpose

Lets the app be reached from other devices on the same network, such as a phone, without exposing Claude Code transcripts and delete actions to anyone else on that network. Local-only use stays the default and stays frictionless.

## ADDED Requirements

### Requirement: Local-only by default, network access is opt-in
By default the app SHALL accept connections only from the machine it runs on. The user SHALL be able to opt in to serving other devices on the network with an explicit start option, and only then SHALL the app accept connections from other machines. The port SHALL default to 8501 and be changeable by the user.

#### Scenario: Default start
- **WHEN** the app is started without the network option
- **THEN** a browser on another device on the network can't connect to it

#### Scenario: Network start
- **WHEN** the app is started with the network option
- **THEN** a browser on another device on the same network can reach it at the machine's address and the chosen port

#### Scenario: Custom port
- **WHEN** the user starts the app with port 9000
- **THEN** it is served on port 9000, and the addresses it prints use 9000

### Requirement: Other devices must present an access token
A request that comes from anywhere other than the machine the app runs on SHALL be refused, with no dashboard data and no page content returned, unless it carries the app's access token. This SHALL apply to every path the app serves, including its data endpoints and its web page files. Requests from the same machine SHALL NOT need a token. A refused request SHALL receive an unauthorized response with a short message telling the user to open the address printed when the server started.

#### Scenario: No token from another device
- **WHEN** a phone on the network requests any page or data address without the token
- **THEN** it receives an unauthorized response and none of the app's data

#### Scenario: Wrong token
- **WHEN** a phone requests the app with an incorrect token
- **THEN** it receives an unauthorized response and none of the app's data

#### Scenario: Same machine needs no token
- **WHEN** a browser on the machine running the app opens it at localhost with no token
- **THEN** the app loads normally

#### Scenario: Request relayed by a proxy or tunnel
- **WHEN** a request reaches the app from the same machine but carries a marker that it was forwarded on behalf of another client, as a tunnel or reverse proxy running on the machine would add
- **THEN** it is treated as coming from another device and needs the token

#### Scenario: Delete requires the token too
- **WHEN** a device on the network sends a delete request for a session or project without the token
- **THEN** it is refused and nothing is deleted

### Requirement: Token is set once and stays valid across restarts
The access token SHALL be taken from an environment setting when the user provides one. Otherwise the app SHALL generate a random token of at least 128 bits the first time it runs with network access, store it on the machine outside version control, and reuse it on later runs. The token SHALL NOT change merely because the app is restarted. The user SHALL be able to replace it by deleting the stored token or changing the environment setting.

#### Scenario: Generated once
- **WHEN** the app is started with the network option twice in a row and no token is configured
- **THEN** both starts use the same token

#### Scenario: Environment setting wins
- **WHEN** an access token is provided through the environment setting
- **THEN** that token is the one required, and no token is generated

#### Scenario: Token is not committed
- **WHEN** a token has been generated and the project is inspected with version control
- **THEN** the stored token file is ignored by version control

### Requirement: Opening a link once signs the device in
Opening the app's address with the token attached SHALL sign that browser in: the browser SHALL be remembered so later visits to the plain address work without the token, and the token SHALL be removed from the address bar and browser history entry so it is not left visible or copied along with the page address. A device that is signed in SHALL be signed in for later sessions until the token is replaced. Opening the address with a wrong token SHALL NOT sign the device in.

#### Scenario: First visit from a phone
- **WHEN** the user opens the printed address with the token on a phone
- **THEN** the dashboard loads and the address shown in the browser no longer contains the token

#### Scenario: Later visit
- **WHEN** that phone later opens the plain address without the token
- **THEN** the dashboard loads

#### Scenario: Token replaced
- **WHEN** the token is changed on the server
- **THEN** a phone signed in with the old token is refused until it opens a link with the new one

### Requirement: Cross-site and rebinding requests are refused
The app SHALL NOT allow web pages from other sites to read its data or trigger its delete actions through the user's browser. A request that comes from the same machine but names a host other than localhost or a loopback address in its address SHALL be refused, so a web page can't reach the local app by pointing its own name at the machine.

#### Scenario: Other site's page
- **WHEN** a page served from another website tries to call the app's data or delete address from the user's browser
- **THEN** the browser is not given access to the response and no delete occurs

#### Scenario: Rebinding
- **WHEN** a request arrives from the same machine but with a host name that is not localhost or a loopback address
- **THEN** it is refused

### Requirement: Identifiers from requests can't reach outside Claude's files
A session identifier or project path received in a request SHALL be validated before it is used to locate a file. A session identifier that is not a well-formed identifier (letters, digits, and dashes only) SHALL be refused. A request SHALL only ever read or delete files inside Claude Code's own transcript storage and configuration. The working directory used to find a session's transcript SHALL be determined by the server from its own records of that session, not supplied by the client.

#### Scenario: Path traversal attempt
- **WHEN** a request supplies a session identifier such as `../../secrets`
- **THEN** it is refused and no file outside Claude's transcript storage is read or deleted

#### Scenario: Unknown session
- **WHEN** a request names a well-formed session identifier that has no transcript
- **THEN** it receives a not-found response

#### Scenario: Client-supplied directory is ignored
- **WHEN** a request for a session's detail includes a working directory that differs from the one the server has recorded for that session
- **THEN** the server uses its own record

### Requirement: Startup tells the user how to open the app
When the app starts it SHALL print the address to open on the machine itself. When started with the network option it SHALL also print, for each of the machine's network addresses, the full address including the token, and a scannable code (QR) for the first of them, so the user can open it on a phone without typing the token. It SHALL also state that the connection is not encrypted and that the token protects only against other devices that do not have it, so the option should only be used on a network the user trusts. If the web interface has not been built, the app SHALL still start, SHALL say clearly that the web interface is missing and how to build it, and SHALL NOT serve a broken page.

#### Scenario: Network start output
- **WHEN** the app is started with the network option
- **THEN** it prints a local address, one address with the token for each network address the machine has, a scannable code, and the note that traffic is unencrypted

#### Scenario: Interface not built
- **WHEN** the app is started before the web interface has been built
- **THEN** it prints that the interface is missing and the command that builds it, and requests for pages return a message saying the same instead of an error page
