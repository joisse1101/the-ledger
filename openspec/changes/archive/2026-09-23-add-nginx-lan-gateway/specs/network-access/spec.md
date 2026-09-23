## MODIFIED Requirements

### Requirement: Local-only by default, network access is opt-in
By default the API and the frontend SHALL each accept connections only from the machine they run
on, with no start option of their own to change that. Network access SHALL be opt-in only at a
separate, single gateway component: the user SHALL be able to start a containerized reverse-proxy
gateway that listens on the network and forwards requests to the local API and frontend, and only
while that gateway is running SHALL other devices on the network be able to reach the app. Each of
the API's, the frontend's, and the gateway's ports SHALL default to a fixed value and be changeable
by the user.

#### Scenario: Default start
- **WHEN** the app is started (API and frontend) without the gateway running
- **THEN** a browser on another device on the network can't connect to it

#### Scenario: Network start
- **WHEN** the API and frontend are running locally and the gateway is also started
- **THEN** a browser on another device on the same network can reach the app at the machine's
  address and the gateway's chosen port

#### Scenario: Custom port
- **WHEN** the user starts the API, the frontend, or the gateway on a non-default port
- **THEN** it is served on that port, and any address the app prints for it uses that port

### Requirement: Token is set once and stays valid across restarts
The access token SHALL be taken from an environment setting when the user provides one. Otherwise
the app SHALL generate a random token of at least 128 bits the first time the API runs, store it on
the machine outside version control, and reuse it on later runs, whether or not the gateway is ever
started. The token SHALL NOT change merely because the app is restarted. The user SHALL be able to
replace it by deleting the stored token or changing the environment setting.

#### Scenario: Generated once
- **WHEN** the API is started twice in a row and no token is configured
- **THEN** both starts use the same token

#### Scenario: Environment setting wins
- **WHEN** an access token is provided through the environment setting
- **THEN** that token is the one required, and no token is generated

#### Scenario: Token is not committed
- **WHEN** a token has been generated and the project is inspected with version control
- **THEN** the stored token file is ignored by version control

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

### Requirement: Startup tells the user how to open the app
When the app's backend starts it SHALL print the address of the app's frontend to open on the
machine itself, and note that the frontend must be running for that address to answer. When the
gateway starts it SHALL print, for each of the machine's network addresses, the gateway's full
address including the token, and a scannable code (QR) for the first of them, so the user can open
it on a phone without typing the token. It SHALL also state that the connection is not encrypted
and that the token protects only against other devices that do not have it, so the gateway should
only be started on a network the user trusts. If the web interface has not been built, starting the
frontend SHALL say clearly that it is missing and how to build it, and SHALL NOT serve a broken
page.

#### Scenario: Network start output
- **WHEN** the gateway is started
- **THEN** it prints one gateway address with the token for each network address the machine has, a
  scannable code, and the note that traffic is unencrypted

#### Scenario: Interface not built
- **WHEN** the frontend is started before the web interface has been built
- **THEN** it says clearly that the interface is missing and gives the command that builds it,
  instead of serving a broken page

## ADDED Requirements

### Requirement: A single gateway is the network's only entry point
A containerized reverse-proxy gateway SHALL be the only component of the app that ever binds an
address reachable from other devices on the network. The API and the frontend SHALL each bind only
to the machine they run on, with no configuration able to change that. The gateway SHALL route
requests under one path prefix to the API and every other request to the frontend, so a device on
the network reaches both through one address and port. The gateway SHALL forward requests to the
API and frontend in a way that the API can distinguish from a same-machine request made directly
(for example, by adding a forwarded-for marker), so the API's existing local/remote distinction and
token requirement apply to every request the gateway relays without change.

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
