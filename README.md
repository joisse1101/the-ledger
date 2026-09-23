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

Three top-level folders, one per service, each self-contained:

- `api/` — the FastAPI backend: `server.py` and its supporting modules (`banner.py`,
  `security.py`, `live_snapshot.py`, `overview_stats.py`, `transcript_query.py`), the
  data layer that actually knows how to read Claude Code's on-disk files
  (`claude_db.py`, `claude_projects.py`, `claude_transcripts.py`, `claude_sessions.py`,
  `claude_context.py`), its tests (`api/tests/`), `requirements*.txt`, `pyproject.toml`,
  and its own `.venv`/`.ledger` (both gitignored). It only ever serves `/api/*` — no
  pages, no static files.
- `web/` — the React + Vite frontend. Built once with `npm run build`, then served by
  its own process (`vite preview`), entirely separate from the API.
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

While actively working on the frontend, `npm run dev` (in place of `npm run build` +
`npm run preview`) hot-reloads on save and proxies `/api` to the backend on
http://localhost:8501, instead of requiring a rebuild for every change.

## Run from another device

To reach the dashboard from a phone, tablet, or another computer on your network, pass
`--lan` to the API and `-- --host` to the frontend's preview command — both need to be
running, and the frontend needs to already be built (see above):

```powershell
cd api
python server.py --lan
```

```powershell
cd web
npm run preview -- --host
```

`--lan` binds the API to your network interfaces instead of just this machine, and it
prints the frontend's URL, a QR code, and an access token for each address it finds —
scanning the QR (or opening the printed link) signs that device in: the token is stored
in that browser and stripped from the address bar, then sent as a header on every
request from then on. A device that hasn't opened that link sees an empty, signed-out
shell instead of your data.

Windows will prompt to allow Python through the firewall the first time you run with
`--lan` — allow it on **Private networks**. The other device also needs to reach the
frontend's port, not just the API's, so if you have a firewall prompt for the frontend
process too, allow that as well.

Only do this on a network you trust: the connection is plain HTTP, not HTTPS, so the
token and your session data aren't encrypted in transit — anyone else on the same
network could read them.

**Rotating the token.** If you've shared the link and want to revoke access, delete
`api/.ledger/token` and restart the API; it generates a fresh one on the next `--lan` run,
and every device using the old token will need the new link.

`--host`/`--port`/`--frontend-port` (or the `LEDGER_HOST`/`LEDGER_PORT`/
`LEDGER_FRONTEND_PORT` env vars) override the API's address/port and the port it expects
the frontend on, if you need something other than the defaults — keep `--frontend-port`
in sync with whatever port you actually run `npm run preview` on.

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
and the FastAPI app end to end (auth, CORS, routes) via `TestClient`.

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
