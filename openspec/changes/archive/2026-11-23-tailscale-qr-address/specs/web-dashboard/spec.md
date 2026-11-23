# Spec Delta

## MODIFIED Requirements

### Requirement: The Remote mode switch is shown only on the machine running the app
The Live list SHALL show Remote mode, its state (off, starting, ready, or failed with a reason), and
when ready how long until it turns itself off. On the machine running the app it SHALL be a switch
the user can flip, with a button next to it that opens the sign-in code in a modal; the button SHALL
be usable only while Remote mode is ready. The modal SHALL show the scannable code and, under it, the
gateway's address without the token. When the machine has more than one kind of address (Tailscale
and LAN) the modal SHALL also offer a choice between them, with Tailscale selected first, and
choosing one SHALL change the code and the address shown; with only one kind it SHALL show no
choice. While Remote mode is starting the switch SHALL show that it is
working and SHALL NOT report it as on. On any other device it SHALL be read-only text with no switch
and no code button, since only a local request can change Remote mode or see the code.

#### Scenario: Switch on this machine
- **WHEN** the Live list is open on the machine running the app
- **THEN** a Remote mode switch is shown and flipping it turns Remote mode on or off

#### Scenario: Starting
- **WHEN** the user turns Remote mode on and the gateway is still coming up
- **THEN** the switch shows that it is starting, and the code button is disabled

#### Scenario: Show the code
- **WHEN** Remote mode is ready and the user selects the code button
- **THEN** a modal shows the scannable code with the gateway's address under it, and the address
  does not contain the token

#### Scenario: Tailscale selected first
- **WHEN** the modal opens on a machine with both a Tailscale and a LAN address
- **THEN** the Tailscale choice is selected and the code and address shown are the Tailscale ones

#### Scenario: Switch to the LAN address
- **WHEN** the user chooses LAN in the modal
- **THEN** the code and the address under it change to the LAN ones, and neither contains a stale
  Tailscale address

#### Scenario: One kind of address
- **WHEN** the machine has only a LAN address (or only a Tailscale one)
- **THEN** the modal shows its code with no choice control

#### Scenario: Failure is explained
- **WHEN** Remote mode could not start
- **THEN** the switch is off and the reason is shown

#### Scenario: Read-only on another device
- **WHEN** the Live list is open on a device that isn't the machine running the app
- **THEN** Remote mode's state is shown as text, with no control to change it and no way to show the
  code
