# CLAUDE.md

Guidance for Claude Code when working in this repository. Detail lives in `wiki/`; read the page
for the area you're touching (routing table below) rather than guessing from the code.

## Project

A dashboard for your local Claude Code sessions and projects (Overview, Sessions, Projects): an
API-only FastAPI backend (`api/`) plus a React + Vite frontend (`web/`), readable from other devices
on the network through a containerized Nginx gateway (`gateway/`) and a shared access token.

## Layout

Exactly six top-level folders (four services, `widget/` and the shared `scripts/`):

- `api/` — the backend: every Python module, its tests, `requirements*.txt`, `pyproject.toml`, and
  its own gitignored `.venv`, `.ledger`, `.history`. All application Python lives here.
- `web/` — the frontend.
- `gateway/` — the Nginx reverse proxy, the only thing that grants LAN access.
- `hooks/` — Claude Code toast hooks plus dashboard-coupled scripts.
- `widget/` — the Electron desktop widget: an always-on-top, read-only live-sessions window with its own
  `package.json`, startup scripts and tests. Talks to the backend on loopback only; imports nothing
  from `web/`.
- `scripts/` — `Ledger-Common.ps1`, the PowerShell helper (`.env`, ports, prerequisites, dependency
  stamps) dot-sourced by the start, install, widget and hook scripts. Its tests are
  `api/tests/test_ledger_common.py`. It also holds the docs tooling `check_docs.py` and
  `build_wiki.py` (Python, standard library only) with tests in `scripts/tests/`.

The root holds only cross-cutting docs and tooling (`README.md`, `wiki/`, `openspec/`,
`.env.example`) and `Install-Ledger.ps1` / `Start-Ledger.ps1` / `Stop-Ledger.ps1`.

## Commands

The venv already exists at `api/.venv`; use `api\.venv\Scripts\python.exe` rather than recreating it.
The API and the frontend are two processes on two ports, chosen from 8501-8599 and saved (8501 and
8502 are the first picks).

```powershell
.\Install-Ledger.ps1            # setup, once: widget shortcut, toast hooks, relay hook, backup task
.\Start-Ledger.ps1              # backend + frontend + widget; -Mode dev, -NoWidget, -Remote adds the gateway
.\Stop-Ledger.ps1

cd api; pytest                  # Python tests, run from api/ (that's where pyproject.toml is)
cd api; pytest ../scripts/tests   # docs tooling tests (not collected by a plain `pytest`)
cd web; npm test                # Vitest
cd web; npm run build           # tsc --noEmit, then vite build; a type error fails it
cd widget; npm test; npm run build   # widget: Vitest, then tsc
.\widget\Start-Widget.ps1       # widget + the backend it needs (no frontend, no Docker)
python scripts/check_docs.py    # docs check, from the repo root: links, code paths, size budgets
```

## Conventions

- Requirements live in `openspec/specs/<capability>/spec.md`. Check there for what a feature must
  do before inferring it from the code.
- Docs are `wiki/*.md`, the source of truth. Edit them here, never in the GitHub wiki (it is
  overwritten on publish). When behavior changes, update the affected page in the same PR.
- Keep this file under 8 KB and nested `CLAUDE.md` files under 4 KB; they hold commands, conventions
  and pointers, not explanation. Don't use `@` imports (they load eagerly).
- Link wiki pages as `[text](Page-Name.md)`.

## Where to read

| Working on | Read |
|---|---|
| Running, ports, `.env`, scheduled backup task | [Setup and run](wiki/Contributing/Setup-And-Run.md) |
| Tests | [Testing](wiki/Contributing/Testing.md) |
| SQLite snapshot, `api/app/repositories/` modules | [Backend: data layer](wiki/Backend/Data-Layer.md) |
| `history.db`, `backup_history.py` | [Backend: history store](wiki/Backend/History-Store.md) |
| `/api/*` routes | [Backend: API routes](wiki/Backend/API-Routes.md) |
| Auth, locality, CSRF (`security.py`) | [Backend: security](wiki/Backend/Security.md) |
| Live prompts, Remote mode, open-repo | [Backend: live sessions and prompts](wiki/Backend/Live-Sessions-And-Prompts.md) |
| Overview stats, transcript queries | [Backend: stats and queries](wiki/Backend/Stats-And-Queries.md) |
| `web/src/api/` (token, client, queries) | [Frontend: API layer](wiki/Frontend/Api-Layer.md) |
| App shell, nav, theme, tokens | [Frontend: shell and theme](wiki/Frontend/Shell-And-Theme.md) |
| Live and All session pages | [Frontend: sessions page](wiki/Frontend/Sessions-Page.md) |
| Overview page and charts | [Frontend: overview page](wiki/Frontend/Overview-Page.md) |
| Projects page | [Frontend: projects page](wiki/Frontend/Projects-Page.md) |
| Files page, file-drop routes | [Frontend: files page](wiki/Frontend/Files-Page.md), [Backend: API routes](wiki/Backend/API-Routes.md) |
| `ButtonSelector`, `ConfirmDialog`, formatting | [Frontend: shared components](wiki/Frontend/Shared-Components.md) |
| Nginx gateway, HTTPS, LAN access | [Gateway](wiki/Services/Gateway.md) |
| Toast hooks, relay hook | [Hooks](wiki/Services/Hooks.md) |
| Desktop widget, its startup scripts | [Widget](wiki/Services/Widget.md) |
| Folder layout, OpenSpec, other repo files | [Repository layout](wiki/Contributing/Repository-Layout.md) |
| Code style and standards | [Coding standards](wiki/Contributing/Coding-Standards.md) |

The full index is [Home](wiki/Home.md). `api/`, `web/` and `hooks/` also have their own
`CLAUDE.md` with local rules.

<!-- jois-init:docs begin -->
## Where the docs are

- The docs live in `wiki/` as nested pages. They are the source of truth.
- The GitHub wiki is a one-way copy. Never edit it; the next publish overwrites it.
- Read the page for your topic before you change the code it describes. Update it in the same change.
- Run `python scripts/check_docs.py` after any docs or path change.

| If you work on | Read first |
| --- | --- |
| Anything (start here) | [Home](wiki/Home.md) |

Add one row per topic folder as `wiki/` grows.
<!-- jois-init:docs end -->
