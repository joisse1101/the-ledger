# Setup and run

Two scripts at the repo root do the setup and the running:

```powershell
.\Install-Ledger.ps1   # once, optional: the extras (widget shortcut, toast hooks, relay hook, backup task)
.\Start-Ledger.ps1     # every time: checks, repairs, starts and verifies
```

`Install-Ledger.ps1` offers each extra one at a time and says first what it does, what it changes on
the machine and what declining means; it installs only what you accept. Accepting the widget shortcut
also installs the widget's packages up front. Each extra has its own switch (`-Shortcut`, `-Autostart`,
`-ToastHooks`, `-RelayHook`, `-BackupTask`, each `ask`/`yes`/`no`) and `-Yes` accepts the rest; with no
console to ask on, an unanswered extra is skipped. Running it again updates what is installed in
place and duplicates nothing. See [Hooks](Hooks.md) and [Widget](Widget.md) for the extras themselves.

`Start-Ledger.ps1` needs [Python](https://www.python.org/downloads/) and
[Node.js](https://nodejs.org/en/download) (and Docker with `-Remote`); when one is missing it names it,
prints the download page and starts nothing. It then creates or repairs the backend's venv, the
frontend and widget packages and the Electron binary, checking each against `requirements*.txt` or
`package-lock.json` (a hash recorded inside the folder it describes), so an empty or stale folder is
rebuilt instead of failing later.

The same steps by hand, inside `api/`, if you'd rather not use the scripts:

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The venv lives at `api/.venv` (activate it, or invoke `api\.venv\Scripts\python.exe` /
`api\.venv\Scripts\pytest.exe` directly) rather than recreating it by hand once it exists.

The frontend needs Node.js in addition to the Python setup above. It's built once (`npm run build`)
and then served by `vite preview`, which serves only the already-built `web/dist` — it doesn't
rebuild on save. `npm run dev` (hot-reloading, proxies `/api` to the backend) is available instead
while actively working on the frontend, but isn't what's used for normal local use.

The Projects page's Source, Issues and PRs columns need `git` and, for the counts, the
[GitHub CLI](https://cli.github.com/) (`gh`) signed in on the machine running the backend
(`gh auth login`). `gh` is optional: without it, or while signed out or offline, the counts show `--`
and nothing else changes.

**Two processes, two ports, every time** — the API only ever serves `/api/*`; the frontend is
always its own separate process:

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

Open the frontend's URL (http://localhost:8502 by default), not the API's — the API has no page to
show you.

**Or start everything at once** with the root `Start-Ledger.ps1`: after the prerequisite and
dependency checks it runs the two processes above (each in its own window, so their logs/Ctrl+C stay
independent), then the desktop widget once the backend answers `/api/meta`. It then checks each piece,
prints a summary with the addresses, and exits non-zero if the backend, frontend or widget is not up
(`-StartupTimeoutSeconds`, default 180, is how long it waits). A backend already answering on the
chosen port is reused, and a widget that is already running is left alone. `Stop-Ledger.ps1` stops
exactly what the start launched (backend, frontend and widget PIDs recorded to the root
`.ledger-run.json`, gitignored; a reused backend or already-running widget has none, so it is left
running) and any gateway container, however it was started. The gateway is not part of the default
start: it comes up through **Remote mode** (the switch in the Ledger or the widget; see
[Gateway](Gateway.md)), or with `-Remote` here:

```powershell
.\Start-Ledger.ps1              # build mode (default) — matches normal local use
.\Start-Ledger.ps1 -Mode dev    # backend + frontend as hot-reloading dev servers instead
.\Start-Ledger.ps1 -NoWidget    # backend + frontend only
.\Start-Ledger.ps1 -Remote      # also turn Remote mode on: Docker, the gateway, then the sign-in QR
.\Stop-Ledger.ps1               # stop what the start launched, and the gateway
```

`-NoGateway` is still accepted but does nothing. `-Mode` changes how both the backend and frontend
windows start. `build` runs `npm run build` + `npm run preview` and starts the backend
without `--reload`; `dev` runs `npm run dev` and starts the backend with `python -m app
--reload` (uvicorn restarts the process on any saved change under `api/`).

**Ports are chosen once and stay the same.** For each of the backend, frontend and gateway the first
of these that applies wins: an explicit `-BackendPort`/`-FrontendPort`/`-GatewayPort`, a value in the
root `.env`, the port saved by an earlier run (`.ledger-ports.json` at the repo root, gitignored), or
the first free port in 8501-8599, which is then saved. The widget and the install scripts read the same
saved ports. A saved port that something else now holds is replaced by a free one, except a saved
backend port held by this app's own backend, which is reused. When the relay hook is installed for a
different backend port than the one chosen, the start says so and offers to reinstall it: it asks
first with a console, and reinstalls and says so with none or with `-Yes`.

`python -m app --reload` (also usable directly, outside `Start-Ledger.ps1`) only works because uvicorn
is given `"app.main:app"` as an import string rather than the already-constructed `app` object — that
lets it re-import the module fresh in a new subprocess on every change, which is also why the
backend's startup banner in the terminal is only printed for the very first start of a `--reload`
session (the freshly re-imported module never runs `main()` again).

**One place to see every port at a glance**: copy root `.env.example` to `.env` (gitignored) and
edit `BACKEND_PORT`/`FRONTEND_PORT`/`GATEWAY_PORT` there. `Start-Gateway.ps1`/
`gateway/docker-compose.yml` read it directly — it's the source of truth for what port Nginx
proxies `/api/*` and `/` to inside the container. The backend and frontend themselves are still
separate local processes that don't read this file: if you change `BACKEND_PORT`/`FRONTEND_PORT`
away from the defaults (8501/8502), also pass `python -m app --port <BACKEND_PORT>` and
`npm run preview -- --port <FRONTEND_PORT>` so they actually run on the ports the gateway expects,
or the gateway will fail to reach them. A custom `BACKEND_PORT` also needs to be set in the
frontend process's own environment (e.g. `BACKEND_PORT=<port> npm run preview -- --port
<FRONTEND_PORT>`) — `web/vite.config.ts`'s own `/api` proxy (used for direct, non-gateway access)
reads it from `process.env.BACKEND_PORT` (default `8501`), separately from the port the gateway's
Nginx is told to target.

**Keeping session history past Claude Code's own retention window**: `api/backup_history.py` (see
[Data layer](Backend-Data-Layer.md)) needs to actually run on a schedule to be useful — the app itself never
triggers it. `Install-Ledger.ps1` offers to register the daily Windows Task Scheduler entry for it
(`Start-Ledger.ps1` no longer installs it). The script it calls,
`hooks\ledgerScripts\Install-HistoryBackupTask.ps1`, can also be run directly, and registers or
updates that same entry:
`api\.venv\Scripts\python.exe backup_history.py`, "Start in" `api\`, run as the logged-in user with
no elevation, daily. Re-running it updates the existing task in place rather than duplicating it;
the paired `Uninstall-HistoryBackupTask.ps1` alongside it removes the task again:

```powershell
cd hooks\ledgerScripts
.\Install-HistoryBackupTask.ps1              # daily at 14:00 by default
.\Install-HistoryBackupTask.ps1 -Time 23:30  # or pick a different trigger time
.\Uninstall-HistoryBackupTask.ps1            # remove it
```

Removing it is also one flag on the root stop script: `.\Stop-Ledger.ps1 -UninstallBackupTask`. If you'd rather set the task up (or tear it down) by hand
than run a script, the two scripts themselves are the reference — they're the definitive list of
exactly which fields to set (program, arguments, working directory, trigger, logon type, run level),
so reading them and replicating those same fields in Task Scheduler's UI produces the same task.

Trigger it manually once after creating it (`Start-ScheduledTask -TaskName 'Ledger History
Backup'`, or right-click the task in Task Scheduler → Run) to confirm it works: inspect
`api/.history/history.db`'s row count/contents before and after (via the `sqlite3` CLI, e.g.
`sqlite3 api/.history/history.db "SELECT COUNT(*) FROM transcripts"`, or Python's builtin `sqlite3`
module if that CLI isn't installed), or check `Get-ScheduledTaskInfo -TaskName 'Ledger History
Backup'`'s `LastTaskResult` (`0` = success). Daily is deliberately decoupled from whether
the backend is even running — this project isn't meant to run as an always-on daemon, so a trigger
tied to the app's own uptime could miss the backup for weeks.
