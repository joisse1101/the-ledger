# api/ — FastAPI backend

Run everything from this folder (`pyproject.toml` is here). Use `.venv\Scripts\python.exe`.

| Working on | Read |
|---|---|
| `app/repositories/`, SQLite snapshot | [Backend-Data-Layer](../wiki/Backend-Data-Layer.md) |
| `history.db`, `backup_history.py` | [Backend-History-Store](../wiki/Backend-History-Store.md) |
| Routes in `app/routers/` | [Backend-API-Routes](../wiki/Backend-API-Routes.md) |
| `api/app/core/security.py`, locality, token | [Backend-Security](../wiki/Backend-Security.md) |
| Pending prompts, Remote mode | [Backend-Live-Sessions-And-Prompts](../wiki/Backend-Live-Sessions-And-Prompts.md) |
| `api/app/domain/overview_stats.py`, `api/app/domain/transcript_query.py` | [Backend-Overview-And-Queries](../wiki/Backend-Overview-And-Queries.md) |
| Test layout | [Testing](../wiki/Testing.md) |

## Local rules

- General standards: toolkit rules (`toolkit/install/Install-Toolkit.ps1`, `-Scope project` works).
- Tests use the `isolated_db` fixture (`~/.claude.json`, `~/.claude/projects/`).
- Layers in `app/`: `routers` (HTTP only) -> `repositories` / `domain` -> `core`; `schemas` shape JSON,
  `infra` wraps the OS, Docker and QR; `deps.py` holds the shared singletons. Imports point downward only.
- Run the server with `python -m app` from `api/`. `backup_history.py`, `gateway_signin.py` and
  `check_docs.py` stay at the `api/` root: scheduled tasks and scripts run them by path.
- Delete routes and Remote-mode switching check `is_local` in the route.
- No `CORSMiddleware`; the frontend only calls relative `/api` paths.
- `api/` runs `hooks/scripts/Open-ClaudeRepoWindow.ps1` for open-repo, so keep that path stable.
- Docs: `python check_docs.py` checks `wiki/` and every `CLAUDE.md`. Update the wiki page when a
  route or module changes.
