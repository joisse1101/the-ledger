# The Ledger

A little dashboard for keeping an eye on your Claude Code usage. If you run Claude Code
across a bunch of projects and terminals, it's easy to lose track of what's actually
running, how a past session went, or how much you've been spending. This app reads the
files Claude Code already keeps on your machine and puts them in one place so you don't
have to go digging.

## What you can do with it

**Get the big picture.** The Overview page has a donut chart breaking down every
session you've ever run by project, plus a panel of headline numbers next to it —
total projects, sessions, and messages, how long your sessions tend to run (average,
longest, shortest), and what they've cost (average, most expensive, cheapest, total).
Tap or hover the longest/shortest/cheapest/most-expensive figures to see which project
and session they came from.

**See what's running right now.** The Sessions page has a "Live" table that shows every
Claude Code process currently running on your machine — which project it's in, what
it's doing, when it last updated. It refreshes itself every couple of seconds, so you
can just leave it open in a tab while you work.

**Look back at every session you've ever run.** Below that is an "All" table pulling
from your session transcripts, going back as far as Claude Code has kept them. It'll
show you how many messages a session had and roughly what it cost, so you can spot the
expensive ones. This table is a manual refresh (there's a ⟳ button) since scanning every
transcript on every tick would be slow.

**Check which projects you've used Claude Code in.** The Projects page lists every
directory you've run or trusted Claude Code in, along with the last session's cost,
CLI version, lines changed, and any MCP servers configured for it.

It also works from your phone or another device on the same network — see "Run from
another device" below — and each device remembers its own light/dark theme preference.

## Layout

Four top-level folders, one per service, each self-contained, plus a pair of scripts at
the root (`Start-Ledger.ps1`/`Stop-Ledger.ps1`) that start/stop all three together — see
"Run" and "Run from another device" below:

- `api/` — the FastAPI backend: `server.py` and its supporting modules (`banner.py`,
  `security.py`, `live_snapshot.py`, `overview_stats.py`, `transcript_query.py`), the
  data layer that actually knows how to read Claude Code's on-disk files
  (`claude_db.py`, `claude_projects.py`, `claude_transcripts.py`, `claude_sessions.py`,
  `claude_context.py`), its tests (`api/tests/`), `requirements*.txt`, `pyproject.toml`,
  and its own `.venv`/`.ledger` (both gitignored). It only ever serves `/api/*` — no
  pages, no static files.
- `web/` — the React + Vite frontend. Built once with `npm run build`, then served by
  its own process (`vite preview`), entirely separate from the API.
- `gateway/` — a small containerized Nginx reverse proxy (needs Docker Desktop). It's
  the only thing that ever exposes the dashboard to another device on your network; the
  API and frontend themselves always stay bound to this machine only. See "Run from
  another device" below.
- `hooks/` — Windows toast notifications for Claude Code's hook events, unrelated to
  the dashboard (see `hooks/README.md`).

## Setup

Create and activate a virtual environment inside `api/` (Windows PowerShell):

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install Python dependencies (still in `api/`):

```powershell
pip install -r requirements.txt
```

You'll also need [Node.js](https://nodejs.org/) installed for the frontend.

## Run

The API and the frontend are two separate processes on two separate ports.

**Terminal 1 — the API** (from `api/`, with its venv active):

```powershell
cd api
python server.py
```

**Terminal 2 — build and serve the frontend** (from `web/`; `npm run build` only needs
re-running after you pull frontend changes, not on every start):

```powershell
cd web
npm ci
npm run build
npm run preview
```

Open the URL `npm run preview` prints (http://localhost:4173 by default) — not the
API's address, which has no page to show you.

While actively working on either side, run them in "dev" mode instead: `npm run dev` (in
place of `npm run build` + `npm run preview`) hot-reloads the frontend on save and
proxies `/api` to the backend on http://localhost:8501; `python server.py --reload`
does the same for the backend, restarting itself whenever a file under `api/` changes.

**Or start both at once** from the repo root:

```powershell
.\Start-Ledger.ps1              # build mode — matches the two terminals above
.\Start-Ledger.ps1 -Mode dev    # both as hot-reloading dev servers instead
```

It opens the backend and frontend each in their own window (so their logs and Ctrl+C
stay independent), and `.\Stop-Ledger.ps1` stops exactly those two windows again without
touching anything else you have open.

## Run from another device

The API and frontend themselves never bind beyond this machine, no matter what — the
only thing that ever grants access from a phone, tablet, or another computer is a small
containerized Nginx gateway (`gateway/`, requires Docker Desktop; Windows/Mac only). With
the API and frontend already running (see "Run" above), start it:

```powershell
cd gateway
.\Start-Gateway.ps1
```

Or skip straight to all three with `.\Start-Ledger.ps1` from the repo root — it starts
the gateway too unless you pass `-NoGateway`.

Either way, once it's up you'll see a sign-in link and QR code printed for every address
this machine is reachable at, e.g. `http://<address>:8080/?token=<token>`. Opening that
link (or scanning the QR) on another device signs it in — the token is stored in that
browser and stripped from the address bar, then sent as a header on every request from
then on. A device that hasn't opened that link sees an empty, signed-out shell instead of
your data.

Windows will prompt to allow Docker/the gateway through the firewall the first time —
allow it on **Private networks**.

Only do this on a network you trust: the connection is plain HTTP, not HTTPS, so the
token and your session data aren't encrypted in transit — anyone else on the same
network could read them.

Stop the gateway on its own with `cd gateway && .\Stop-Gateway.ps1` (or `.\Stop-Ledger.ps1`
from the root, which also stops the API/frontend windows `Start-Ledger.ps1` opened) — it
doesn't touch the API/frontend processes either way.

**Rotating the token.** If you've shared the link and want to revoke access, delete
`api/.ledger/token` and restart the API; it generates a fresh one on next start, and
every device using the old token will need the new link.

One place to see/change every port (gateway, API, frontend) is the root `.env` — copy
`.env.example` to `.env` and edit it; see `CLAUDE.md`'s "Setup & Run" for the full
precedence rules and how to keep the API/frontend processes in sync with a custom port.

## Testing

Install dev dependencies (from `api/`; this includes `requirements.txt` plus `pytest`):

```powershell
cd api
pip install -r requirements-dev.txt
```

Run the Python test suite (from `api/`, where its `pyproject.toml` lives):

```powershell
pytest
```

Tests live in `api/tests/`, one file per module under test. They cover the pure
parsing/aggregation logic (cost math, time-range filtering, chart data prep), the
SQLite-backed read/write/delete paths in `claude_db.py`, `claude_projects.py`, and
`claude_transcripts.py` (via an `isolated_db` fixture — see `api/tests/conftest.py` — that
points `claude_db` at a throwaway `tmp_path` instead of your real `~/.claude.json` /
`~/.claude/projects/`, so running the suite never touches your actual Claude Code data),
and the FastAPI app end to end (auth, routes) via `TestClient`.

Run the frontend tests (from `web/`):

```powershell
npm test
```

And check the frontend still builds cleanly (also fails on a TypeScript type error):

```powershell
npm run build
```

## A couple of things worth knowing

- Cost numbers are estimates, worked out from token counts in the transcripts — Claude
  Code doesn't write a dollar figure to disk anywhere except your most recent session
  per project. If you've used a model this app doesn't recognize yet, its cost won't be
  counted.
- The "Live" table can occasionally show a session that's no longer actually running —
  Claude Code doesn't always clean up its registry file the moment a process exits.
- Each device remembers its own light/dark theme preference locally (it follows your
  system setting until you flip the toggle yourself), so there's nothing to configure
  and nothing that syncs between devices.
