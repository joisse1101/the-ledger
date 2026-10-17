# network-access Specification

## Purpose

Lets the app be reached from other devices on the same network, such as a phone, without exposing Claude Code transcripts and delete actions to anyone else on that network. Local-only use stays the default and stays frictionless.

## Requirements

### Requirement: Local-only by default, network access is opt-in
By default the API and the frontend SHALL each accept connections only from the machine they run
on, with no start option of their own to change that. Network access SHALL be opt-in only at a
separate, single gateway component: the user SHALL be able to start a containerized reverse-proxy
gateway that listens on the network and forwards requests to the local API and frontend, and only
while that gateway is running SHALL other devices on the network be able to reach the app. Starting
the app SHALL NOT start the gateway unless the user asks for it, either by turning Remote mode on or
by an explicit start option. Each of the API's, the frontend's, and the gateway's ports SHALL
default to a fixed value and be changeable by the user.

#### Scenario: Default start
- **WHEN** the app is started (API and frontend) without asking for remote access
- **THEN** the gateway is not running and a browser on another device on the network can't connect
  to it

#### Scenario: Start with remote access requested
- **WHEN** the app is started with the explicit option to include the gateway
- **THEN** the gateway is started, Remote mode is on, and a browser on another device on the same
  network can reach the app at the machine's address and the gateway's chosen port

#### Scenario: Network start
- **WHEN** the API and frontend are running locally and Remote mode is turned on
- **THEN** a browser on another device on the same network can reach the app at the machine's
  address and the gateway's chosen port

#### Scenario: Custom port
- **WHEN** the user starts the API, the frontend, or the gateway on a non-default port
- **THEN** it is served on that port, and any address the app prints for it uses that port

### Requirement: Other devices must present an access token for data
A request to any of the app's data endpoints (session, project, overview, and live data; refresh;
answering a live session's pending prompt; opening a session's repo window) that comes from
anywhere other than the machine the app runs on SHALL be refused, with no dashboard data returned and
no action taken, unless it carries the app's access token. Requests from the same machine SHALL NOT
need a token. A refused request SHALL receive an unauthorized response with a short message telling
the user to open the address printed when the server started. Delete actions and switching Remote
mode follow the stricter, local-only rules defined by "Delete actions require a local request" and
"Switching Remote mode requires a local request" instead of this token rule. Whether another device
may see or answer a pending prompt at all additionally depends on Remote mode, defined by the
remote-session-control capability. The one exception to the token rule is a file-drop download
link, defined by the file-drop capability: a single-use, short-lived link for one named file that
is itself the credential and reaches nothing else. The app's page shell (the files that render the empty dashboard before any data loads) is not itself
gated by the token — see the following requirement.

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
- **WHEN** a data request reaches the app from the same machine but carries a marker that it was
  forwarded on behalf of another client, as a tunnel or reverse proxy running on the machine would
  add
- **THEN** it is treated as coming from another device and needs the token

#### Scenario: Delete requires the token too
- **WHEN** a device on the network sends a delete request for a session or project without the token
- **THEN** it is refused and nothing is deleted

#### Scenario: Prompt-answer and open-repo actions require the token too
- **WHEN** a device on the network sends a prompt-answer or open-repo-window request without the
  token
- **THEN** it is refused and no action is taken

#### Scenario: A file download link needs no token but nothing else does
- **WHEN** a phone without the token opens a valid file-drop download link, and then requests any
  other data address
- **THEN** the link returns its one file, and every other request is refused as unauthorized

### Requirement: The page shell carries no data and needs no token
The static files that render the app's empty page (before any data has loaded) SHALL be servable to any device that can reach them, on the same machine or over the network, without the token. This is safe only because that shell contains no session, project, or transcript data by itself — every scenario in the previous requirement still applies to the data that fills it in.

#### Scenario: Shell loads without a token
- **WHEN** a device on the network without the token requests the app's page
- **THEN** the empty page loads, but no dashboard data appears until a valid token is presented for the data requests it makes

#### Scenario: A public shell is not a data leak
- **WHEN** the page shell is inspected without a token
- **THEN** it contains no session, project, or transcript content

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

### Requirement: Cross-site and rebinding requests are refused
The app SHALL NOT allow web pages from other sites to read its data or trigger its delete actions
through the user's browser. The API SHALL NOT grant any web origin permission to read its responses
across origins, since every legitimate caller — the dev server, `vite preview`, and the gateway —
always reaches it through a same-origin proxy rather than calling it directly. A request that comes
from the same machine but names a host other than localhost or a loopback address in its address
SHALL be refused, so a web page can't reach the local app by pointing its own name at the machine.

#### Scenario: Other site's page
- **WHEN** a page served from another website tries to call the app's data or delete address from
  the user's browser
- **THEN** the browser is not given access to the response and no delete occurs

#### Scenario: Another site can't read a same-machine response either
- **WHEN** a page open in the same browser, served from somewhere other than the app's own
  frontend, requests the app's data address directly (which needs no token from that browser's
  machine)
- **THEN** the request may reach the app, but the browser still refuses to let that page's script
  read the response, because no origin is ever granted permission to

#### Scenario: Rebinding
- **WHEN** a request arrives from the same machine but with a host name that is not localhost or a
  loopback address
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

### Requirement: A single gateway is the network's only entry point
A containerized reverse-proxy gateway SHALL be the only component of the app that ever binds an
address reachable from other devices on the network. The API and the frontend SHALL each bind only
to the machine they run on, with no configuration able to change that. The gateway SHALL route
requests under one path prefix to the API and every other request to the frontend, so a device on
the network reaches both through one address and port. The gateway SHALL forward requests to the
API and frontend in a way that the API can distinguish from a same-machine request made directly
(for example, by adding a forwarded-for marker), so the API's existing local/remote distinction and
token requirement apply to every request the gateway relays without change. The gateway SHALL
terminate HTTPS for every connection from another device, using a self-signed certificate generated
for it, and SHALL NOT also listen for plain HTTP — HTTPS SHALL be its only listener. It SHALL
continue to forward requests to the API and frontend over plain HTTP, since both stay bound to
loopback on the same machine and are never reachable except through the gateway.

#### Scenario: Gateway is the only network-reachable surface
- **WHEN** the API and frontend are running (without the gateway) and a device on the network tries
  to reach either directly
- **THEN** the connection is refused, because neither binds an address other devices can reach

#### Scenario: One address for both frontend and API
- **WHEN** a device on the network requests a data address under the gateway's path prefix for the
  API
- **THEN** the gateway forwards it to the API; a request for any other path is forwarded to the
  frontend

#### Scenario: Gateway-relayed requests are treated as remote
- **WHEN** the gateway forwards a request to the API on behalf of a device on the network
- **THEN** the API treats it as coming from another device and requires the access token, even
  though the gateway itself runs on the same machine as the API

#### Scenario: Gateway serves HTTPS, backend stays HTTP
- **WHEN** a device on the network connects to the gateway's address
- **THEN** the connection uses HTTPS with the gateway's self-signed certificate, even though the
  gateway's own requests to the API and frontend behind it are plain HTTP

### Requirement: Delete actions require a local request
Deleting a session or project SHALL be refused unless the request comes from the machine the app
runs on, using the same locality test the rest of the app uses (loopback address, no forwarded-for
marker). This applies even when the request carries a valid access token: the access token widens
what a remote device can read and act on, but it SHALL NOT by itself be sufficient to authorize a
delete from another device. A local request needs no token for this either, per the existing
local-request rule.

#### Scenario: Local delete succeeds
- **WHEN** a browser on the machine running the app sends a delete request for a session or project
- **THEN** it proceeds normally, without needing a token

#### Scenario: Remote delete refused even with a valid token
- **WHEN** a device on the network sends a delete request for a session or project and presents the
  correct access token
- **THEN** it is refused and nothing is deleted

### Requirement: Switching Remote mode requires a local request
Turning Remote mode on or off SHALL be refused unless the request comes from the machine the app
runs on, using the same locality test the rest of the app uses (loopback address, no forwarded-for
marker). This applies even when the request carries a valid access token: a token lets another
device see and answer prompts while Remote mode is on, but SHALL NOT let it change Remote mode. A
local request needs no token for this, per the existing local-request rule.

#### Scenario: Local switch succeeds
- **WHEN** a browser on the machine running the app turns Remote mode on or off
- **THEN** it takes effect, without needing a token

#### Scenario: Remote switch refused even with a valid token
- **WHEN** a device on the network tries to turn Remote mode on or off and presents the correct
  access token
- **THEN** it is refused and Remote mode is unchanged

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
