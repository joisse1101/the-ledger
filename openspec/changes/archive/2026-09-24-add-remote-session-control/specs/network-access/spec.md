## MODIFIED Requirements

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
remote-session-control capability. The app's page shell (the files that render the empty dashboard before any data loads) is not itself
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
- **WHEN** the gateway is started
- **THEN** it prints one gateway address using `https://` with the token for each network address the
  machine has, a scannable code, and the note that the connection is encrypted with a self-signed
  certificate the browser will warn about

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

## ADDED Requirements

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
