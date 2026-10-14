# api/ — FastAPI backend

Run everything from this folder (`pyproject.toml` is here). Use `.venv\Scripts\python.exe`.

| Working on | Read |
|---|---|
| `claude_*.py`, SQLite snapshot | [Backend-Data-Layer](../wiki/Backend-Data-Layer.md) |
| `history.db`, `backup_history.py` | [Backend-History-Store](../wiki/Backend-History-Store.md) |
| Routes in `server.py` | [Backend-API-Routes](../wiki/Backend-API-Routes.md) |
| `security.py`, locality, token | [Backend-Security](../wiki/Backend-Security.md) |
| Pending prompts, Remote mode | [Backend-Live-Sessions-And-Prompts](../wiki/Backend-Live-Sessions-And-Prompts.md) |
| `overview_stats.py`, `transcript_query.py` | [Backend-Overview-And-Queries](../wiki/Backend-Overview-And-Queries.md) |
| Test layout | [Testing](../wiki/Testing.md) |

## Local rules

- General standards: toolkit rules (`toolkit/install/Install-Toolkit.ps1`, `-Scope project` works).
- Tests use the `isolated_db` fixture (`~/.claude.json`, `~/.claude/projects/`).
- The `claude_*.py` modules are the data layer.
- Delete routes and Remote-mode switching check `is_local` in the route.
- No `CORSMiddleware`; the frontend only calls relative `/api` paths.
- `api/` runs `hooks/scripts/Open-ClaudeRepoWindow.ps1` for open-repo, so keep that path stable.
- Docs: `python check_docs.py` checks `wiki/` and every `CLAUDE.md`. Update the wiki page when a
  route or module changes.
