# Guide: Remote access

Open the dashboard on your phone or another computer on the same network, see live sessions, answer their prompts and move files.
[Remote mode](Glossary.md#remote-mode) is the switch that allows this. It is off by default.

## Before you begin

- Install Docker Desktop on the PC. Remote mode needs it.
- Start the Ledger. See [Getting started](Guide-Getting-Started.md).
- Use a network you trust. The connection uses a self-signed certificate. See the note below.

## Turn on Remote mode

1. On the PC that runs the Ledger, open **Sessions** in the top bar.
2. Flip the **Remote mode** switch above the list.
3. Wait. The page shows progress such as "Starting Docker…", "Starting the web interface…" and "Starting the gateway…".
4. Read the hover text on the switch for the time left. Remote mode turns itself off after a set time.
5. If it fails, the reason is shown beside the switch.
6. Alternative: use the **Remote** button in the desktop widget, or start with `.\Start-Ledger.ps1 -Remote`.

Only the PC that runs the Ledger can flip the switch. Other devices see "Remote mode: on", "starting" or "off" as text.

## Sign in on another device

1. On the PC, click **QR code** next to the switch. It is usable only while Remote mode is on.
2. Read the window titled "Open on another device". It shows a QR code and the address below it.
3. On the other device, scan the code with the camera.
4. Accept the browser's one-time certificate warning. It is expected, because the [gateway](Glossary.md#gateway) makes its own certificate.
5. The dashboard loads. The sign-in code is an [access token](Glossary.md#access-token) in the link. The browser removes it from the address bar and remembers you.
6. Next time, open the plain address. You stay signed in until Remote mode is turned off.
7. Click **Close** on the PC to hide the code.

If a device says "This device isn't signed in", Remote mode was turned off and on again. Click **QR code** again and scan the new code.

## What you can do from the other device

- See live sessions and answer their prompts. See [Live sessions](Guide-Live-Sessions.md).
- Browse the Overview, Manage Sessions and Manage Projects pages.
- Use **Files** to send and fetch files. See [Files](Guide-Files.md).
- You cannot delete sessions, projects or files, change Remote mode, open Settings or see the sign-in code. Those work only on the PC.

## Turn it off

1. Flip the **Remote mode** switch off on the PC.
2. Know that every device is signed out when it turns off.

## The certificate warning

- The warning appears because the address is a local network address, which has no certificate from a public authority.
- The traffic is still encrypted, but the browser cannot confirm who it is talking to.
- Do this only on a network you trust.

## Checked and unchecked

- Checked: control names and messages above against `RemoteModeControl.tsx`, `RemoteQrDialog.tsx`, `ServerBanner.tsx` and `Nav.tsx`.
- Checked: the sign-in, token and local-only behaviour against `openspec/specs/network-access/spec.md` and `openspec/specs/remote-session-control/spec.md`.
- Unchecked: the first-time Windows firewall prompt for Docker. [Gateway](Gateway.md) says to allow it on Private networks, and it was not seen here.
- Unchecked: scanning with a real phone.

## More detail

- [Gateway](Gateway.md) explains the container, the certificate and the ports.
- [Security](Backend-Security.md) explains how the token is checked.
- `openspec/specs/network-access/spec.md` and `openspec/specs/remote-session-control/spec.md` hold the requirements, including how long Remote mode lasts.
