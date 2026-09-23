# network-access Specification

## Purpose

Lets the app be reached from other devices on the same network, such as a phone, without exposing Claude Code transcripts and delete actions to anyone else on that network. Local-only use stays the default and stays frictionless.

## Requirements

### Requirement: Local-only by default, network access is opt-in
By default each of the app's two processes — the API and the frontend — SHALL accept connections only from the machine it runs on. The user SHALL be able to opt in to serving other devices on the network with an explicit start option on each process, and only then SHALL that process accept connections from other machines. Each process's port SHALL default to a fixed value and be changeable by the user.

#### Scenario: Default start
- **WHEN** the app is started without the network option on either process
- **THEN** a browser on another device on the network can't connect to it

#### Scenario: Network start
- **WHEN** both processes are started with their network option
- **THEN** a browser on another device on the same network can reach the app at the machine's address and the chosen ports

#### Scenario: Custom port
- **WHEN** the user starts a process on a non-default port
- **THEN** it is served on that port, and any address the app prints for it uses that port

### Requirement: Other devices must present an access token for data
A request to any of the app's data endpoints (session, project, overview, and live data; refresh; delete actions) that comes from anywhere other than the machine the app runs on SHALL be refused, with no dashboard data returned, unless it carries the app's access token. Requests from the same machine SHALL NOT need a token. A refused request SHALL receive an unauthorized response with a short message telling the user to open the address printed when the server started. The app's page shell (the files that render the empty dashboard before any data loads) is not itself gated by the token — see the following requirement.

#### Scenario: No token from another device
- **WHEN** a phone on the network requests any data address without the token
- **THEN** it receives an unauthorized response and none of the app's data

#### Scenario: Wrong token
- **WHEN** a phone requests data with an incorrect token
- **THEN** it receives an unauthorized response and none of the app's data

#### Scenario: Same machine needs no token
- **WHEN** a browser on the machine running the app requests data from localhost with no token
- **THEN** the data is returned normally

#### Scenario: Request relayed by a proxy or tunnel
- **WHEN** a data request reaches the app from the same machine but carries a marker that it was forwarded on behalf of another client, as a tunnel or reverse proxy running on the machine would add
- **THEN** it is treated as coming from another device and needs the token

#### Scenario: Delete requires the token too
- **WHEN** a device on the network sends a delete request for a session or project without the token
- **THEN** it is refused and nothing is deleted

### Requirement: The page shell carries no data and needs no token
The static files that render the app's empty page (before any data has loaded) SHALL be servable to any device that can reach them, on the same machine or over the network, without the token. This is safe only because that shell contains no session, project, or transcript data by itself — every scenario in the previous requirement still applies to the data that fills it in.

#### Scenario: Shell loads without a token
- **WHEN** a device on the network without the token requests the app's page
- **THEN** the empty page loads, but no dashboard data appears until a valid token is presented for the data requests it makes

#### Scenario: A public shell is not a data leak
- **WHEN** the page shell is inspected without a token
- **THEN** it contains no session, project, or transcript content

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
The app SHALL NOT allow web pages from other sites to read its data or trigger its delete actions through the user's browser, even when the app's frontend and its data endpoints are served from different addresses of their own. A request that comes from the same machine but names a host other than localhost or a loopback address in its address SHALL be refused, so a web page can't reach the local app by pointing its own name at the machine.

#### Scenario: Other site's page
- **WHEN** a page served from another website tries to call the app's data or delete address from the user's browser
- **THEN** the browser is not given access to the response and no delete occurs

#### Scenario: Another site can't read a same-machine response either
- **WHEN** a page open in the same browser, served from somewhere other than the app's own frontend, requests the app's data address directly (which needs no token from that browser's machine)
- **THEN** the request may reach the app, but the browser still refuses to let that page's script read the response, because only the app's own frontend address is allowed to

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
When the app's backend starts it SHALL print the address of the app's frontend to open on the machine itself, and note that the frontend must be running for that address to answer. When started with the network option it SHALL also print, for each of the machine's network addresses, the frontend's full address including the token, and a scannable code (QR) for the first of them, so the user can open it on a phone without typing the token. It SHALL also state that the connection is not encrypted and that the token protects only against other devices that do not have it, so the option should only be used on a network the user trusts. If the web interface has not been built, starting the frontend SHALL say clearly that it is missing and how to build it, and SHALL NOT serve a broken page.

#### Scenario: Network start output
- **WHEN** the app's backend is started with the network option
- **THEN** it prints the frontend's local address, one frontend address with the token for each network address the machine has, a scannable code, and the note that traffic is unencrypted

#### Scenario: Interface not built
- **WHEN** the frontend is started before the web interface has been built
- **THEN** it says clearly that the interface is missing and gives the command that builds it, instead of serving a broken page
