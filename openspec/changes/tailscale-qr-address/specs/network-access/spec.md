# Spec Delta

## MODIFIED Requirements

### Requirement: The sign-in code is available to the local machine as an image
While Remote mode is ready, the app SHALL offer the machine running it the gateway's sign-in code
as an image, together with the gateway's address for display and the time left until Remote mode
turns itself off. The app SHALL offer one such code for each of the machine's usable network
addresses, each labelled Tailscale (an address in 100.64.0.0/10) or LAN (any other), and SHALL mark
the Tailscale address as the default when there is one, otherwise the first address. Each code SHALL encode the
full HTTPS sign-in address for its address, including the token created for this Remote session. The
display address SHALL be the HTTPS address and port only, never the token. Because the codes contain
the access token, they SHALL be refused for any request that is not from the machine running the
app, even with a valid token. While Remote mode is off or not yet ready there SHALL be no code.

#### Scenario: Local request while ready
- **WHEN** Remote mode is ready and the machine running the app asks for the sign-in code
- **THEN** it receives a scannable image of the full sign-in address, the address without the
  token, and the time left, all for the default address

#### Scenario: Tailscale address is the default
- **WHEN** the machine has both a Tailscale address and a LAN address
- **THEN** the default code and display address use the Tailscale address, and the LAN address is
  offered as an alternative labelled LAN

#### Scenario: Only a LAN address
- **WHEN** the machine has no Tailscale address
- **THEN** the only code, and the default, is for the LAN address

#### Scenario: Code matches the session
- **WHEN** Remote mode is switched off and on again and the code is requested each time
- **THEN** the two codes differ, and only the second one signs a device in

#### Scenario: Other device asks
- **WHEN** a device on the network asks for the sign-in code and presents the correct access token
- **THEN** it is refused and no code or token is revealed

#### Scenario: Not ready
- **WHEN** Remote mode is off, starting, or failed and the machine running the app asks for the code
- **THEN** no code is returned and the response says Remote mode is not ready
