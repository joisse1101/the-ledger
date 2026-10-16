## MODIFIED Requirements

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

### Requirement: Startup tells the user how to open the app
When the app's backend starts it SHALL print the address of the app's frontend to open on the
machine itself, and note that the frontend must be running for that address to answer. When the
gateway starts it SHALL print, for each of the machine's network addresses, the gateway's full
HTTPS address including the token, and a scannable code (QR) for the first of them, so the user can
open it on a phone without typing the token. It SHALL also state that the connection is encrypted
using the gateway's own self-signed certificate — which the browser will not recognize as trusted
and will warn about the first time, needing to be accepted once — and that, self-signed certificate
aside, the token remains what protects against other devices that don't have it, so the gateway
should still only be started on a network the user trusts. If the web interface has not been built,
starting the frontend SHALL say clearly that it is missing and how to build it, and SHALL NOT serve a
broken page.

#### Scenario: Network start output
- **WHEN** the gateway is started from a command line
- **THEN** it prints one gateway address using `https://` with the token for each network address the
  machine has, a scannable code, and the note that the connection is encrypted with a self-signed
  certificate the browser will warn about

#### Scenario: Interface not built
- **WHEN** the frontend is started before the web interface has been built
- **THEN** it says clearly that the interface is missing and gives the command that builds it,
  instead of serving a broken page

## ADDED Requirements

### Requirement: The sign-in code is available to the local machine as an image
While Remote mode is ready, the app SHALL offer the machine running it the gateway's sign-in code
as an image, together with the gateway's address for display and the time left until Remote mode
turns itself off. The code SHALL encode the same full HTTPS sign-in address, including the token,
that the gateway prints for the machine's first network address. The display address SHALL be the
HTTPS address and port only, never the token. Because the code contains the access token, it SHALL be
refused for any request that is not from the machine running the app, even with a valid token. While
Remote mode is off or not yet ready there SHALL be no code.

#### Scenario: Local request while ready
- **WHEN** Remote mode is ready and the machine running the app asks for the sign-in code
- **THEN** it receives a scannable image of the full sign-in address, the address without the
  token, and the time left

#### Scenario: Other device asks
- **WHEN** a device on the network asks for the sign-in code and presents the correct access token
- **THEN** it is refused and no code or token is revealed

#### Scenario: Not ready
- **WHEN** Remote mode is off, starting, or failed and the machine running the app asks for the code
- **THEN** no code is returned and the response says Remote mode is not ready
