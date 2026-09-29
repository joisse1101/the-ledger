# Setup and run

Create/activate the venv and install Python dependencies, all inside `api/`:

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

A `.venv` already exists at `api/.venv` with dependencies installed — activate it
(`api\.venv\Scripts\Activate.ps1`, or invoke `api\.venv\Scripts\python.exe` /
`api\.venv\Scripts\pytest.exe` directly) rather than searching for or recreating one.

The frontend needs Node.js in addition to the Python setup above. It's built once (`npm run build`)
and then served by `vite preview`, which serves only the already-built `web/dist` — it doesn't
rebuild on save. `npm run dev` (hot-reloading, proxies `/api` to the backend) is available instead
while actively working on the frontend, but isn't what's used for normal local use.

**Two processes, two ports, every time** — the API only ever serves `/api/*`; the frontend is
always its own separate process:

```powershell
# Terminal 1, in api/: the API (defaults to http://localhost:8501)
cd api
python server.py

# Terminal 2, in web/: build once, then serve the built frontend (defaults to http://localhost:4173)
cd web
npm ci
npm run build
npm run preview
```

Open the frontend's URL (http://localhost:4173 by default), not the API's — the API has no page to
show you.

**Or start everything at once** with the root `Start-Ledger.ps1`, which runs the two processes
above (each in its own window, so their logs/Ctrl+C stay independent) plus the gateway
(see [Gateway](Gateway.md)), in one call — paired with `Stop-Ledger.ps1` to stop exactly what it started (backend/frontend
window PIDs recorded to the root `.ledger-run.json`, gitignored, and the gateway container):

```powershell
.\Start-Ledger.ps1              # build mode (default) — matches normal local use
.\Start-Ledger.ps1 -Mode dev    # backend + frontend as hot-reloading dev servers instead
.\Start-Ledger.ps1 -NoGateway   # skip the gateway container (this machine only)
.\Stop-Ledger.ps1               # stop the backend/frontend windows and the gateway
```

`-Mode` changes how both the backend and frontend windows start — the gateway always starts the
same way either way. `build` runs `npm run build` + `npm run preview` and starts the backend
without `--reload`; `dev` runs `npm run dev` and starts the backend with `python server.py
--reload` (uvicorn restarts the process on any saved change under `api/`). Port overrides
(`-BackendPort`/`-FrontendPort`/`-GatewayPort`) follow the same `.env` precedence as
`gateway\Start-Gateway.ps1` (see [Gateway](Gateway.md)).

`server.py --reload` (also usable directly, outside `Start-Ledger.ps1`) only works because uvicorn
is given `"server:app"` as an import string rather than the already-constructed `app` object — that
lets it re-import the module fresh in a new subprocess on every change, which is also why the
backend's startup banner and access-token print in the terminal are only accurate for the very
first start of a `--reload` session (each subsequent restart re-provisions the same stored token
silently in `lifespan()`, since the freshly re-imported module never runs `main()` again).

**One place to see every port at a glance**: copy root `.env.example` to `.env` (gitignored) and
edit `BACKEND_PORT`/`FRONTEND_PORT`/`GATEWAY_PORT` there. `Start-Gateway.ps1`/
`gateway/docker-compose.yml` read it directly — it's the source of truth for what port Nginx
proxies `/api/*` and `/` to inside the container. The backend and frontend themselves are still
separate local processes that don't read this file: if you change `BACKEND_PORT`/`FRONTEND_PORT`
away from the defaults (8501/4173), also pass `python server.py --port <BACKEND_PORT>` and
`npm run preview -- --port <FRONTEND_PORT>` so they actually run on the ports the gateway expects,
or the gateway will fail to reach them. A custom `BACKEND_PORT` also needs to be set in the
frontend process's own environment (e.g. `BACKEND_PORT=<port> npm run preview -- --port
<FRONTEND_PORT>`) — `web/vite.config.ts`'s own `/api` proxy (used for direct, non-gateway access)
reads it from `process.env.BACKEND_PORT` (default `8501`), separately from the port the gateway's
Nginx is told to target.

**Keeping session history past Claude Code's own retention window**: `api/backup_history.py` (see
[Data layer](Backend-Data-Layer.md)) needs to actually run on a schedule to be useful — the app itself never
triggers it. Register a daily Windows Task Scheduler entry for it with
`hooks\ledgerScripts\Install-HistoryBackupTask.ps1`, which registers or updates that same entry:
`api\.venv\Scripts\python.exe backup_history.py`, "Start in" `api\`, run as the logged-in user with
no elevation, daily. Re-running it updates the existing task in place rather than duplicating it;
the paired `Uninstall-HistoryBackupTask.ps1` alongside it removes the task again:

```powershell
cd hooks\ledgerScripts
.\Install-HistoryBackupTask.ps1              # daily at 14:00 by default
.\Install-HistoryBackupTask.ps1 -Time 23:30  # or pick a different trigger time
.\Uninstall-HistoryBackupTask.ps1            # remove it
```

Or fold either into the root scripts as one flag: `.\Start-Ledger.ps1 -InstallBackupTask` /
`.\Stop-Ledger.ps1 -UninstallBackupTask`. If you'd rather set the task up (or tear it down) by hand
than run a script, the two scripts themselves are the reference — they're the definitive list of
exactly which fields to set (program, arguments, working directory, trigger, logon type, run level),
so reading them and replicating those same fields in Task Scheduler's UI produces the same task.

Trigger it manually once after creating it (`Start-ScheduledTask -TaskName 'Ledger History
Backup'`, or right-click the task in Task Scheduler → Run) to confirm it works: inspect
`api/.history/history.db`'s row count/contents before and after (via the `sqlite3` CLI, e.g.
`sqlite3 api/.history/history.db "SELECT COUNT(*) FROM transcripts"`, or Python's builtin `sqlite3`
module if that CLI isn't installed), or check `Get-ScheduledTaskInfo -TaskName 'Ledger History
Backup'`'s `LastTaskResult` (`0` = success). Daily is deliberately decoupled from whether
`server.py` is even running — this project isn't meant to run as an always-on daemon, so a trigger
tied to the app's own uptime could miss the backup for weeks.
