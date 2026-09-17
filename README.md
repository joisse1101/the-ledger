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

## Setup

Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run

```powershell
streamlit run app.py
```

The app will open at http://localhost:8501.

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
