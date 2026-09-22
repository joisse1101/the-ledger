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
Hover the longest/shortest/cheapest/most-expensive figures to see which project and
session they came from.

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

There's also a dark mode toggle in the sidebar, if you're into that.

> **Note:** this repo is mid-migration from the Streamlit UI below to a React frontend
> served by a FastAPI backend (`api/server.py`), which also adds access from other
> devices on your network. Both currently work; see "Run the new web app" below for
> the one that's replacing Streamlit. The `## Setup` section applies to either.

## Layout

- `streamlit_app/` — the Streamlit UI (`app.py` + `views/`).
- `api/` — the FastAPI backend that serves the React frontend (`server.py` and its
  supporting modules: `banner.py`, `security.py`, `live_snapshot.py`,
  `overview_stats.py`, `transcript_query.py`).
- `web/` — the React + Vite frontend `api/server.py` serves once built.
- Everything else at the repo root (`claude_db.py`, `claude_projects.py`,
  `claude_transcripts.py`, `claude_sessions.py`, `claude_context.py`) is the shared
  data layer both the Streamlit app and the API server read from — it isn't specific
  to either UI, so it stays put rather than living under one of the two folders above.

## Setup

Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies (this covers both the Streamlit app and the new FastAPI server):

```powershell
pip install -r requirements.txt
```

## Run

Run this from the repo root, not from inside `streamlit_app/`:

```powershell
streamlit run streamlit_app/app.py
```

The app will open at http://localhost:8501.

## Run the new web app

The new frontend lives in `web/` (React + Vite) and talks to a FastAPI backend
(`api/server.py`); you need Node.js installed in addition to the Python setup above.
Run the Python commands below from the repo root, not from inside `api/`.

**Development** — backend and frontend as separate dev servers, so the frontend
hot-reloads on save:

```powershell
# Terminal 1: the API, on http://localhost:8501
python api/server.py

# Terminal 2: the UI, on http://localhost:5173 (proxies /api to the backend above)
cd web
npm install
npm run dev
```

Open http://localhost:5173.

**Built** — two processes, two ports: the API serves only `/api/*`, and the built
frontend is served separately by Vite's own static server. This is also what's needed
to reach the app from another device (see below):

```powershell
# Terminal 1: build once, then serve the compiled frontend on its own port
cd web
npm ci
npm run build
npm run preview
```

```powershell
# Terminal 2, from the repo root: the API
python api/server.py
```

Open http://localhost:4173 (Vite's own default preview port).

**From another device on your network** (phone, tablet, another computer), pass
`--lan` to the API and `-- --host` to the frontend's preview command — both need to be
running:

```powershell
python api/server.py --lan
```

```powershell
cd web
npm run preview -- --host
```

This requires the frontend to already be built (see above). `--lan` binds the API to
your network interfaces instead of just this machine, and it prints the frontend's URL,
a QR code, and an access token for each — the other device needs the token (baked into
the QR/URL) to sign in; opening that link stores the token on the device and it's used
on every API request from then on. Only do this on a network you trust: the connection
is plain HTTP, so the token and your session data aren't encrypted in transit.
`--host`/`--port`/`--frontend-port` (or the `LEDGER_HOST`/`LEDGER_PORT`/
`LEDGER_FRONTEND_PORT` env vars) override the API's address/port and the port it expects
the frontend on, if you need something other than the defaults — keep `--frontend-port`
in sync with whatever port you actually run `npm run preview` on.

## Testing

Install dev dependencies (this includes `requirements.txt` plus `pytest`):

```powershell
pip install -r requirements-dev.txt
```

Run the test suite:

```powershell
pytest
```

Tests live in `tests/`, one file per module under test (`test_claude_db.py`,
`test_claude_projects.py`, `test_claude_transcripts.py`, `test_claude_sessions.py`,
`test_overview.py`, `test_views.py`). They cover the pure parsing/aggregation logic
(cost math, time-range filtering, chart data prep) and the SQLite-backed
read/write/delete paths in `claude_db.py`, `claude_projects.py`, and
`claude_transcripts.py` — the latter via a `isolated_db` fixture (see
`tests/conftest.py`) that points `claude_db` at a throwaway `tmp_path` instead of your
real `~/.claude.json` / `~/.claude/projects/`, so running the suite never touches your
actual Claude Code data. Streamlit rendering itself (`render_*` functions that call
`st.*` widgets) isn't covered — only the plain functions those pages build their data
from.

## A couple of things worth knowing

- Cost numbers are estimates, worked out from token counts in the transcripts — Claude
  Code doesn't write a dollar figure to disk anywhere except your most recent session
  per project. If you've used a model this app doesn't recognize yet, its cost won't be
  counted.
- The "Live" table can occasionally show a session that's no longer actually running —
  Claude Code doesn't always clean up its registry file the moment a process exits.
- Your dark mode preference is saved locally to a gitignored `.streamlit/theme_pref.json`
  so it survives restarts without cluttering up the repo. Delete that file if you ever
  want to reset back to the default theme.
