# Repository layout

This page explains what the repo contains and where things live: the top-level folders, the root files, the on-disk data and the OpenSpec folder. Read it to find where a change belongs.

## What the project is

A dashboard for viewing your local Claude Code sessions and projects: Overview, Sessions (Live + All), Projects. It's an API-only FastAPI backend (`api/`) plus one React + Vite frontend (`web/`), built so a phone or other device on the same network can read it too, behind a shared access token.

The backend and frontend run as two separate processes on two ports. The API never serves any HTML itself (see [Setup and run](Setup-And-Run.md)).

## Top-level folders

The repo has exactly six top-level folders: `scripts/` plus five self-contained ones.

- `api/` is the backend: every Python module, its tests, `requirements*.txt`, `pyproject.toml`, and its own gitignored `.venv`/`.ledger`/`.history`.
- `web/` is the frontend.
- `gateway/` is the containerized Nginx reverse proxy that's the only thing granting other devices access. It has its own Dockerfile, Nginx config template, and compose file; see [Gateway](Gateway.md).
- `hooks/` holds Claude Code toast hooks, plus dashboard-coupled scripts: a relay hook and the history-backup scheduled-task installer/uninstaller. See [Hooks](Hooks.md).
- `widget/` is the Electron desktop widget: a floating, read-only live-sessions window with its own `package.json`, tests and startup scripts; see [Widget](Widget.md).
- `scripts/` is the shared PowerShell helper, `Ledger-Common.ps1`, dot-sourced by the start, install, widget and hook scripts. It also holds the docs tooling: `check_docs.py`, `build_wiki.py` and their tests in `scripts/tests/`. The helper runs nothing on its own.

## Root files

The root holds only cross-cutting docs and tooling: `README.md`, `CLAUDE.md`, `.gitignore`, `.env.example`, `openspec/`, `.claude/` and `.github/`. It also holds three scripts:

- `Install-Ledger.ps1` is the one-time wizard for the optional extras.
- `Start-Ledger.ps1` starts the app.
- `Stop-Ledger.ps1` stops it.

The start and stop scripts keep two gitignored state files:

- `.ledger-run.json` holds the PIDs of what the start launched.
- `.ledger-ports.json` holds the ports it chose.

The three scripts are kept at root rather than inside any one service folder, since they're the tooling that spans all the services (see [Setup and run](Setup-And-Run.md)). Otherwise nothing at root runs on its own.

## Requirements

The agreed requirements for each shipped capability live in `openspec/specs/` (see the OpenSpec section below). Check there for what a feature is required to do (e.g. `network-access` for the bearer-token auth and separate-origin rules) ahead of inferring it from the code alone.

## On-disk data

The API and frontend both read the same on-disk Claude Code data (`~/.claude.json` and `~/.claude/projects/*/*.jsonl`) via a SQLite snapshot at `api/.ledger/ledger.db`. It is gitignored, and rebuilt from disk on every server start and periodically thereafter. See [Data layer](Backend-Data-Layer.md).

A second, never-wiped SQLite file, `api/.history/history.db`, retains a summary row per session transcript ever scanned. A session therefore survives in Overview/Projects/the All list after Claude Code prunes its `.jsonl` from disk. See [History store](Backend-History-Store.md) and `api/backup_history.py`.

## OpenSpec

The OpenSpec workflow directory. `openspec/specs/` holds the current, agreed specs for shipped capabilities:

- `web-dashboard`
- `responsive-layout`
- `network-access`
- `live-context-gauge`
- `toast-context-line`
- `remote-session-control`

`openspec/changes/` holds proposals in flight, each with `proposal.md`/`design.md`/`tasks.md` plus a spec delta. Completed ones move to `openspec/changes/archive/` and aren't tracked further.

Treat the specs as the authoritative record of what a capability is required to do, ahead of inferring intent from the code alone.

## Other repo files

### Generated and ignored folders

`api/.ledger/` (gitignored) holds the SQLite snapshot (`ledger.db*`; see [Data layer](Backend-Data-Layer.md)). It is recreated as needed and never committed.

`api/.history/` (gitignored) holds the durable `history.db*` (see [History store](Backend-History-Store.md)). Unlike `.ledger/`, it is never recreated or wiped; it's built up over time by `api/backup_history.py`.

`.gitignore` also excludes `web/node_modules/`, `web/dist/`, and root `.env`.

### Config and dependency files

- Root `.env.example` (committed) documents `BACKEND_PORT`/`FRONTEND_PORT`/`GATEWAY_PORT` in one place. Copy it to `.env` (gitignored) to override any of them; see [Setup and run](Setup-And-Run.md) for how each one is actually consumed.
- `api/requirements.txt`: `fastapi`, `uvicorn`, `qrcode`, unpinned. `requirements-dev.txt` adds `pytest` and `httpx` (for FastAPI's `TestClient`).
- `.github/dependabot.yml`: weekly (Monday) npm update PRs for `web/` and `widget/`, with minor and patch bumps grouped into one PR. `api/` is left out because its requirements are unpinned.
- `web/package.json`: React 19, `@tanstack/react-query`, `react-router-dom` and `vega-embed` (dependencies); Vite, TypeScript, Vitest, Testing Library and jsdom (devDependencies). `npm run build` is `tsc --noEmit && vite build`, so a type error fails the build, not just lint. <!-- docs-check: ignore -->
