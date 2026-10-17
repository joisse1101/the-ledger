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
remote-session-control capability. The one exception to the token rule is a file-drop download
link, defined by the file-drop capability: a single-use, short-lived link for one named file that
is itself the credential and reaches nothing else. The app's page shell (the files that render the empty dashboard before any data loads) is not itself
gated by the token — see the following requirement.

#### Scenario: No token from another device
- **WHEN** a phone requests any data address without the token
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
