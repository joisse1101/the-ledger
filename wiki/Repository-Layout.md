# Repository layout

A dashboard for viewing your local Claude Code sessions and projects: Overview, Sessions (Live +
All), Projects. It's an API-only FastAPI backend (`api/`) plus one React + Vite frontend (`web/`),
built so a phone or other device on the same network can read it too, behind a shared access token.
The backend and frontend run as two separate processes/ports; the API never serves any HTML itself (see
[Setup and run](Setup-And-Run.md)).

The repo has exactly five top-level folders, each self-contained: `api/` (the
backend — every Python module, its tests, `requirements*.txt`, `pyproject.toml`, and its own
gitignored `.venv`/`.ledger`/`.history`), `web/` (the frontend), `gateway/` (the containerized Nginx reverse
proxy that's the only thing granting other devices access — its own Dockerfile, Nginx config
template, and compose file; see [Gateway](Gateway.md)), and `hooks/` (Claude
Code toast hooks, plus dashboard-coupled scripts — a relay hook and the history-backup scheduled-task
installer/uninstaller — see [Hooks](Hooks.md)), and `toolkit/` (not a service: tool-neutral reusable
AI-agent skills under `toolkit/skills/<name>/SKILL.md`, agents under `toolkit/agents/` and slash commands
under `toolkit/commands/` (the read-only `/code-audit` is one skill, two agents and one command), plus
`toolkit/install/Install-Skills.ps1` and its `targets.json` that copy them into Claude Code's global or a
project's `.claude/skills|agents|commands/` without silently overwriting a differing copy; independent of the dashboard, see `toolkit/README.md`). The root holds only cross-cutting docs/tooling (`README.md`, `CLAUDE.md`,
`.gitignore`, `.env.example`, `openspec/`, `.claude/`) plus a pair of scripts, `Start-Ledger.ps1`/
`Stop-Ledger.ps1` (and that pair's own gitignored state file, `.ledger-run.json`), kept at root
rather than inside any one service folder since they're the one piece of tooling that spans all
three services (see [Setup and run](Setup-And-Run.md)) — otherwise nothing at root runs on its own.

The agreed requirements for each shipped capability live in `openspec/specs/` (see the OpenSpec section below) — check there for what a feature is required to do (e.g. `network-access` for the
bearer-token auth and separate-origin rules) ahead of inferring it from the code alone.

The API and frontend both read the same on-disk Claude Code data (`~/.claude.json` and
`~/.claude/projects/*/*.jsonl`) via a SQLite snapshot at `api/.ledger/ledger.db` (gitignored, rebuilt
from disk on every server start and periodically thereafter — see [Data layer](Backend-Data-Layer.md)). A second,
never-wiped SQLite file, `api/.history/history.db`, retains a summary row per session transcript
ever scanned, so a session survives in Overview/Projects/the All list after Claude Code prunes its
`.jsonl` from disk — see [History store](Backend-History-Store.md) and `api/backup_history.py`.

## OpenSpec

The OpenSpec workflow directory. `openspec/specs/` holds the current, agreed specs for shipped
capabilities: `web-dashboard`, `responsive-layout`, `network-access`, `live-context-gauge`,
`toast-context-line`, `remote-session-control`, `toolkit-skills`. `openspec/changes/` holds proposals in flight (each with
`proposal.md`/`design.md`/`tasks.md` plus a spec delta); completed ones move to
`openspec/changes/archive/` and aren't tracked further. Treat the specs as the authoritative record
of what a capability is required to do, ahead of inferring intent from the code alone.

## Other repo files

- `api/.ledger/` (gitignored) holds the SQLite snapshot (`ledger.db*` — see [Data layer](Backend-Data-Layer.md))
  and the LAN access token (`token`, see [Security](Backend-Security.md)); both are recreated as needed and
  never committed. `api/.history/` (gitignored) holds the durable `history.db*` — see [History store](Backend-History-Store.md) — which, unlike `.ledger/`, is never recreated or wiped; it's built up over time by
  `api/backup_history.py`. `.gitignore` also excludes `web/node_modules/`, `web/dist/`, and root
  `.env`.
- Root `.env.example` (committed) documents `BACKEND_PORT`/`FRONTEND_PORT`/`GATEWAY_PORT` in one
  place — copy it to `.env` (gitignored) to override any of them; see [Setup and run](Setup-And-Run.md) for how
  each one is actually consumed.
- `api/requirements.txt`: `fastapi`, `uvicorn`, `qrcode` — unpinned. `requirements-dev.txt` adds
  `pytest`, `httpx` (for FastAPI's `TestClient`).
- `web/package.json`: React 19, `@tanstack/react-query`, `react-router-dom`, `vega-embed`
  (dependencies); Vite, TypeScript, Vitest, Testing Library, jsdom (devDependencies). `npm run build`
  is `tsc --noEmit && vite build` — a type error fails the build, not just lint.
