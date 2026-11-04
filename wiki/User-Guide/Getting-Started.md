# Guide: Getting started

Install the Ledger, start it, open the dashboard in your browser and know how signing in works.
You need a Windows PC that already runs Claude Code.

## Before you begin

- Install [Python](https://www.python.org/downloads/) and [Node.js](https://nodejs.org/en/download).
- Open PowerShell in the folder you cloned the Ledger into (the repo root).
- Docker is only needed for [Remote mode](../Glossary.md#remote-mode), covered in [Remote access](Remote-Access.md).

## Install the optional extras (once)

The installer is optional. Skip it if you only want the dashboard.

1. Run `.\Install-Ledger.ps1`.
2. Read what each question says it changes, then answer yes or no.
3. Run it again later if you change your mind. A second run does not duplicate anything.

The extras it can offer:

- The desktop widget shortcut, with a choice to start it when you sign in to Windows. See [Desktop widget](Widget.md).
- Toast hooks and chime hooks. See [Notifications](Notifications.md).
- The relay hook, which lets the dashboard show and answer Claude's prompts. See [Live sessions](Live-Sessions.md).
- A daily backup of your session history.

## Start the Ledger

1. Run `.\Start-Ledger.ps1`.
2. Wait while it checks Python and Node, repairs anything missing, and starts the backend, the frontend and the widget.
3. Read the summary it prints. Each piece is listed as running with its address.
4. If a piece failed, the summary says which one and the command exits with an error.

Useful variations:

- `.\Start-Ledger.ps1 -NoWidget` starts the dashboard without the widget.
- `.\Start-Ledger.ps1 -Mode dev` starts hot-reloading dev servers. Use it only if you are changing the code.
- `.\Start-Ledger.ps1 -Remote` also turns on Remote mode. See [Remote access](Remote-Access.md).

## Open the dashboard

1. Copy the frontend address from the start summary. The first free choice is `http://localhost:8502`, but the summary is the source of truth because ports are chosen once and then saved.
2. Paste it into your browser on the same PC.
3. Use the top bar to move between pages: Sessions (the live list), Overview, Manage Projects and Manage Sessions.

## Sign in

- On the PC that runs the Ledger you do not sign in. The page just opens.
- On another device you scan a sign-in code. See [Remote access](Remote-Access.md).
- A device that is not signed in sees "This device isn't signed in" and the steps to fix it.

## Stop the Ledger

1. Run `.\Stop-Ledger.ps1`.
2. It closes what the start command opened, plus the gateway if one is running.

## Checked and unchecked

- Checked: every script name and switch above against the scripts' parameter lists. `.\Start-Ledger.ps1 -Help` and `.\Stop-Ledger.ps1 -Help` were run and listed the switches used here.
- Unchecked: `.\Install-Ledger.ps1`, `.\Start-Ledger.ps1` and `.\Stop-Ledger.ps1` were not run in full. A run installs software and starts processes, so only their help output and parameter lists were read.
- Unchecked: the exact wording of each installer question.

## More detail

- [Setup and run](../Contributing/Setup-And-Run.md) explains ports, the `.env` file and what the start script checks.
- `openspec/specs/installer/spec.md` and `openspec/specs/app-startup/spec.md` hold the requirements.
