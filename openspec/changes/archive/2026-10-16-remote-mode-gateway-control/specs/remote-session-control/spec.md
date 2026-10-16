## MODIFIED Requirements

### Requirement: Remote mode controls what other devices can do
The app SHALL have a Remote mode that the user turns on before leaving the machine. Turning it on
SHALL make the app reachable from other devices: it SHALL start whatever is not already running that
other devices need (the container runtime, the web interface, and the network gateway), and it SHALL
report its state as off, starting, ready, or failed with a reason. It SHALL be ready only once other
devices can actually connect, and SHALL NOT be reported as on while nothing is listening. While it is
ready, a device other than the machine running the app that presents the access token SHALL be able
to see a session's pending prompts and answer them. While it is off, the network gateway SHALL be
stopped, such a device SHALL see no pending prompts and any attempt to answer one SHALL be refused,
while the machine's own browser and the terminal are unaffected. Only a request from the machine
running the app SHALL be able to turn Remote mode on or off; other devices SHALL be able to see its
state but not change it, even with a valid token. Remote mode SHALL turn itself off after 8 hours,
and after the app's backend restarts. Whenever it turns off, the gateway SHALL be stopped, and so
SHALL the web interface if Remote mode started it; a web interface that was already running SHALL be
left running.

#### Scenario: Remote mode off
- **WHEN** Remote mode is off and a session is waiting on a prompt
- **THEN** another device sees no pending prompt and cannot answer one, the gateway is not running,
  and this machine's dashboard and the terminal still work

#### Scenario: Remote mode on
- **WHEN** Remote mode is ready and a session is waiting on a prompt
- **THEN** another device with the access token sees the prompt and can answer it

#### Scenario: Turning on from nothing
- **WHEN** the container runtime, the web interface and the gateway are all stopped and the user
  turns Remote mode on
- **THEN** Remote mode reports starting while each is brought up in turn, and ready once another
  device can connect

#### Scenario: Something cannot start
- **WHEN** the user turns Remote mode on and a step fails or does not finish in a reasonable time,
  such as the container runtime not being installed
- **THEN** Remote mode reports failed with the reason, is not reported as on, and anything it
  already started is stopped

#### Scenario: Another device tries to switch it
- **WHEN** a device other than the machine running the app tries to turn Remote mode on or off,
  with or without a valid token
- **THEN** it is refused and Remote mode is unchanged, and the switch is not shown on that device

#### Scenario: Expiry
- **WHEN** Remote mode has been on for 8 hours, or the backend restarts
- **THEN** it is off again and the gateway is stopped, including a gateway left running by an
  earlier backend

#### Scenario: Turning off closes only what it opened
- **WHEN** Remote mode is turned off after it started the web interface
- **THEN** the gateway and the web interface it started are stopped

#### Scenario: Web interface was already running
- **WHEN** the web interface was running before Remote mode was turned on, and Remote mode is turned
  off
- **THEN** the gateway is stopped and the web interface keeps running
