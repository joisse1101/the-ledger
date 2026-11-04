# Setup and run

This page explains how to install, start and stop the Ledger, how its ports are chosen, and how to schedule the history backup. Two scripts at the repo root do the work. Remote mode is defined in the [Glossary](../Glossary.md#remote-mode).

```powershell
.\Install-Ledger.ps1   # once, optional: the extras (widget shortcut, chime hooks, toast hooks, relay hook, backup task)
.\Start-Ledger.ps1     # every time: checks, repairs, starts and verifies
```

## Install the extras

`Install-Ledger.ps1` offers each extra one at a time and says first what it does, what it changes on the machine and what declining means. It installs only what you accept. Accepting the widget shortcut also installs the widget's packages up front.

Running it again updates what is installed in place and duplicates nothing. See [Hooks](../Services/Hooks.md) and [Widget](../Services/Widget.md) for the extras themselves.

Each extra has its own switch, and each takes `ask`, `yes` or `no`:

- `-Shortcut`
- `-Autostart`
- `-ChimeHooks`
- `-ToastHooks`
- `-RelayHook`
- `-BackupTask`

`-Yes` accepts the rest. With no console to ask on, an unanswered extra is skipped.

## What the start script checks

`Start-Ledger.ps1` needs [Python](https://www.python.org/downloads/) and [Node.js](https://nodejs.org/en/download), and Docker with `-Remote`. When one is missing it names it, prints the download page and starts nothing.

It then creates or repairs the backend's venv, the frontend and widget packages and the Electron binary. It checks each against `requirements*.txt` or `package-lock.json` (a hash recorded inside the folder it describes), so an empty or stale folder is rebuilt instead of failing later.

## Set up by hand

If you would rather not use the scripts, the same steps by hand, inside `api/`:

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The venv lives at `api/.venv`. Activate it, or invoke `api\.venv\Scripts\python.exe` / `api\.venv\Scripts\pytest.exe` directly, rather than recreating it by hand once it exists.

## Frontend

The frontend needs Node.js in addition to the Python setup above. It is built once (`npm run build`) and then served by `vite preview`. That serves only the already-built `web/dist` and does not rebuild on save.

`npm run dev` (hot-reloading, proxies `/api` to the backend) is available instead while actively working on the frontend, but is not what is used for normal local use.

## Optional tools for the Projects page

The Projects page's Source, Issues and PRs columns need `git` and, for the counts, the [GitHub CLI](https://cli.github.com/) (`gh`) signed in on the machine running the backend (`gh auth login`).

`gh` is optional. Without it, or while signed out or offline, the counts show `--` and nothing else changes.

## Run the two processes

**Two processes, two ports, every time.** The API only ever serves `/api/*`; the frontend is always its own separate process.

```powershell
# Terminal 1, in api/: the API (defaults to http://localhost:8501)
cd api
python -m app

# Terminal 2, in web/: build once, then serve the built frontend (defaults to http://localhost:8502)
cd web
npm ci
npm run build
npm run preview
```

Open the frontend's URL (http://localhost:8502 by default), not the API's. The API has no page to show you.

## Start everything at once

The root `Start-Ledger.ps1` runs the two processes above after the prerequisite and dependency checks. Each runs in its own window, so their logs and Ctrl+C stay independent. It then starts the desktop widget once the backend answers `/api/meta`.

It then checks each piece, prints a summary with the addresses, and exits non-zero if the backend, frontend or widget is not up. `-StartupTimeoutSeconds` (default 180) is how long it waits.

Two things are left alone. A backend already answering on the chosen port is reused, and a widget that is already running is left alone.

`Stop-Ledger.ps1` stops exactly what the start launched. The backend, frontend and widget PIDs are recorded to the root `.ledger-run.json` (gitignored). A reused backend or already-running widget has no recorded PID, so it is left running. It also stops any gateway container, however it was started.

The gateway is not part of the default start. It comes up through **Remote mode** (the switch in the Ledger or the widget; see [Gateway](../Services/Gateway.md)), or with `-Remote` here:

```powershell
.\Start-Ledger.ps1              # build mode (default) — matches normal local use
.\Start-Ledger.ps1 -Mode dev    # backend + frontend as hot-reloading dev servers instead
.\Start-Ledger.ps1 -NoWidget    # backend + frontend only
.\Start-Ledger.ps1 -Remote      # also turn Remote mode on: Docker, the gateway, then the sign-in QR
.\Stop-Ledger.ps1               # stop what the start launched, and the gateway
```

`-NoGateway` is still accepted but does nothing.

### Build and dev mode

`-Mode` changes how both the backend and frontend windows start:

- `build` runs `npm run build` + `npm run preview` and starts the backend without `--reload`.
- `dev` runs `npm run dev` and starts the backend with `python -m app --reload`.

With `--reload`, uvicorn restarts the process on any saved change under `api/`.

### How `--reload` works

`python -m app --reload` is also usable directly, outside `Start-Ledger.ps1`. It only works because uvicorn is given `"app.main:app"` as an import string rather than the already-constructed `app` object. That lets it re-import the module fresh in a new subprocess on every change.

For the same reason, the backend's startup banner in the terminal is printed only for the very first start of a `--reload` session. The freshly re-imported module never runs `main()` again.

## Ports

**Ports are chosen once and stay the same.** For each of the backend, frontend and gateway, the first of these that applies wins:

1. An explicit `-BackendPort`/`-FrontendPort`/`-GatewayPort`.
2. A value in the root `.env`.
3. The port saved by an earlier run (`.ledger-ports.json` at the repo root, gitignored).
4. The first free port in 8501-8599, which is then saved.

The widget and the install scripts read the same saved ports.

A saved port that something else now holds is replaced by a free one. The exception is a saved backend port held by this app's own backend, which is reused.

When the relay hook is installed for a different backend port than the one chosen, the start says so and offers to reinstall it. It asks first with a console, and reinstalls and says so with none or with `-Yes`.

### Set ports in `.env`

**One place to see every port at a glance:** copy root `.env.example` to `.env` (gitignored) and edit `BACKEND_PORT`/`FRONTEND_PORT`/`GATEWAY_PORT` there. `Start-Gateway.ps1` and `gateway/docker-compose.yml` read it directly. It is the source of truth for what port Nginx proxies `/api/*` and `/` to inside the container.

The backend and frontend themselves are still separate local processes that don't read this file. If you change `BACKEND_PORT`/`FRONTEND_PORT` away from the defaults (8501/8502), also pass these so they run on the ports the gateway expects, or the gateway will fail to reach them:

- `python -m app --port <BACKEND_PORT>`
- `npm run preview -- --port <FRONTEND_PORT>`

A custom `BACKEND_PORT` also needs to be set in the frontend process's own environment (e.g. `BACKEND_PORT=<port> npm run preview -- --port <FRONTEND_PORT>`). The `/api` proxy in `web/vite.config.ts` (used for direct, non-gateway access) reads it from `process.env.BACKEND_PORT` (default `8501`). That is separate from the port the gateway's Nginx is told to target.

## Keep session history past Claude Code's retention window

`api/backup_history.py` (see [Data layer](../Backend/Data-Layer.md)) needs to actually run on a schedule to be useful. The app itself never triggers it.

`Install-Ledger.ps1` offers to register the daily Windows Task Scheduler entry for it (`Start-Ledger.ps1` no longer installs it). The script it calls, `hooks\ledgerScripts\Install-HistoryBackupTask.ps1`, can also be run directly, and registers or updates that same entry:

- Program: `api\.venv\Scripts\python.exe backup_history.py`.
- "Start in": `api\`.
- Runs as the logged-in user with no elevation, daily.

Re-running it updates the existing task in place rather than duplicating it. The paired `Uninstall-HistoryBackupTask.ps1` alongside it removes the task again:

```powershell
cd hooks\ledgerScripts
.\Install-HistoryBackupTask.ps1              # daily at 14:00 by default
.\Install-HistoryBackupTask.ps1 -Time 23:30  # or pick a different trigger time
.\Uninstall-HistoryBackupTask.ps1            # remove it
```

Removing it is also one flag on the root stop script: `.\Stop-Ledger.ps1 -UninstallBackupTask`.

### Set the task up by hand

If you would rather set the task up (or tear it down) by hand than run a script, the two scripts themselves are the reference. They are the definitive list of exactly which fields to set (program, arguments, working directory, trigger, logon type, run level). Reading them and replicating those same fields in Task Scheduler's UI produces the same task.

### Check that it works

Trigger it manually once after creating it, with `Start-ScheduledTask -TaskName 'Ledger History Backup'` or by right-clicking the task in Task Scheduler → Run. Then confirm it worked either way:

- Inspect `api/.history/history.db`'s row count or contents before and after. Use the `sqlite3` CLI, e.g. `sqlite3 api/.history/history.db "SELECT COUNT(*) FROM transcripts"`, or Python's builtin `sqlite3` module if that CLI isn't installed.
- Check `Get-ScheduledTaskInfo -TaskName 'Ledger History Backup'`'s `LastTaskResult` (`0` = success).

### Why daily

Daily is deliberately decoupled from whether the backend is even running. This project isn't meant to run as an always-on daemon, so a trigger tied to the app's own uptime could miss the backup for weeks.
