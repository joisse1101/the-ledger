# CLAUDE.md

Guidance for Claude Code when working in this repository. Detail lives in `wiki/`; read the page
for the area you're touching (routing table below) rather than guessing from the code.

## Project

A dashboard for your local Claude Code sessions and projects (Overview, Sessions, Projects): an
API-only FastAPI backend (`api/`) plus a React + Vite frontend (`web/`), readable from other devices
on the network through a containerized Nginx gateway (`gateway/`) and a shared access token.

## Layout

Exactly five top-level folders, each self-contained (four services plus `toolkit/`):

- `api/` — the backend: every Python module, its tests, `requirements*.txt`, `pyproject.toml`, and
  its own gitignored `.venv`, `.ledger`, `.history`. All Python lives here.
- `web/` — the frontend.
- `gateway/` — the Nginx reverse proxy, the only thing that grants LAN access.
- `hooks/` — Claude Code toast hooks plus dashboard-coupled scripts.
- `toolkit/` — not a service: reusable AI-agent skills (`toolkit/skills/<name>/SKILL.md`), agents
  (`toolkit/agents/`), slash commands (`toolkit/commands/`, e.g. the read-only `/code-audit`) and an
  installer (`toolkit/install/Install-Skills.ps1`). Independent of the dashboard; see
  `toolkit/README.md`.

The root holds only cross-cutting docs and tooling (`README.md`, `wiki/`, `openspec/`,
`.env.example`) and `Start-Ledger.ps1` / `Stop-Ledger.ps1`.

## Commands

The venv already exists at `api/.venv`; use `api\.venv\Scripts\python.exe` rather than recreating it.
The API and the frontend are two processes on two ports (8501 and 4173).

```powershell
.\Start-Ledger.ps1              # backend + frontend (+ gateway); -Mode dev for hot reload
.\Stop-Ledger.ps1

cd api; pytest                  # Python tests, run from api/ (that's where pyproject.toml is)
cd web; npm test                # Vitest
cd web; npm run build           # tsc --noEmit, then vite build; a type error fails it
cd api; python check_docs.py    # docs check: links, code paths, size budgets
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
| Running, ports, `.env`, scheduled backup task | [Setup-And-Run](wiki/Setup-And-Run.md) |
| Tests | [Testing](wiki/Testing.md) |
| SQLite snapshot, `claude_*.py` modules | [Backend-Data-Layer](wiki/Backend-Data-Layer.md) |
| `history.db`, `backup_history.py` | [Backend-History-Store](wiki/Backend-History-Store.md) |
| `/api/*` routes | [Backend-API-Routes](wiki/Backend-API-Routes.md) |
| Auth, locality, CSRF (`security.py`) | [Backend-Security](wiki/Backend-Security.md) |
| Live prompts, Remote mode, open-repo | [Backend-Live-Sessions-And-Prompts](wiki/Backend-Live-Sessions-And-Prompts.md) |
| Overview stats, transcript queries | [Backend-Overview-And-Queries](wiki/Backend-Overview-And-Queries.md) |
| `web/src/api/` (token, client, queries) | [Frontend-Api-Layer](wiki/Frontend-Api-Layer.md) |
| App shell, nav, theme, tokens | [Frontend-Shell-And-Theme](wiki/Frontend-Shell-And-Theme.md) |
| Live and All session pages | [Frontend-Sessions](wiki/Frontend-Sessions.md) |
| Overview page and charts | [Frontend-Overview](wiki/Frontend-Overview.md) |
| Projects page | [Frontend-Projects](wiki/Frontend-Projects.md) |
| `ButtonSelector`, `ConfirmDialog`, formatting | [Frontend-Shared-Components](wiki/Frontend-Shared-Components.md) |
| Nginx gateway, HTTPS, LAN access | [Gateway](wiki/Gateway.md) |
| Toast hooks, relay hook | [Hooks](wiki/Hooks.md) |
| Folder layout, OpenSpec, other repo files | [Repository-Layout](wiki/Repository-Layout.md) |
| Code style and standards | [Coding-Standards](wiki/Coding-Standards.md) |

The full index is [Home](wiki/Home.md). `api/`, `web/` and `hooks/` also have their own
`CLAUDE.md` with local rules.
