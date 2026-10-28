# Tasks

## 1. Remote URL parsing

- [x] 1.1 Add `api/app/core/remote_url.py` (`web_url`, `host_label`) with `api/tests/core/test_remote_url.py` covering scp-style, `ssh://`, https with credentials, a `.git` suffix, a non-GitHub host, and a local path or `file://` returning None; verify with `cd api; pytest tests/core/test_remote_url.py`

## 2. Git and gh wrapper

- [x] 2.1 Add `api/app/infra/repo_cli.py` (`RepoCli` with an injected `run`: `remote_url`, `open_counts`; timeout, no console window, None on non-zero exit, timeout, `OSError` or bad JSON, failure logged as key/value with the path) with `api/tests/infra/test_repo_cli.py` using a fake `run`; verify the tests pass, including a missing `gh` and a signed-out `gh`

## 3. Service and endpoint

- [x] 3.1 Add `api/app/services/project_repo_service.py`: for each project from `claude_projects.load_projects()`, resolve url and host, fetch counts only for GitHub, look projects up in a thread pool, and cache per path with a TTL (shorter for failures) and an injected clock; verify with `api/tests/services/test_project_repo_service.py` (GitHub project, non-GitHub, no remote, cache hit, expiry, one project failing without affecting the others)
- [x] 3.2 Add `GET /api/projects/repos` to `api/app/routers/projects.py` and its item shape to `api/app/schemas/projects.py`; the handler takes no parameters; verify with a route test that runs no command for a path outside the known projects and that `api/tests/test_layers.py` still passes
- [x] 3.3 Update `wiki/Backend-API-Routes.md` (the new route), `wiki/Setup-And-Run.md` (`gh` as an optional dependency, `gh auth login`) and `wiki/Backend-Live-Sessions-And-Prompts.md` only if it mentions where `gh`/`git` are called; verify with `cd api; python check_docs.py`

## 4. Frontend

- [x] 4.1 Add the `ProjectRepo` types to `web/src/api/types.ts` and `useProjectRepos()` to `web/src/api/queries.ts` (via `apiFetch`, `staleTime` matching the server TTL); verify with new cases in `queries.test.tsx`
- [x] 4.2 Add Source, Issues and PRs columns to `web/src/components/projects/ProjectsList.tsx`, joined by path, `--` while loading or unavailable, Source as a new-tab link that does not toggle the row; verify with `ProjectsList.test.tsx` (GitHub, non-GitHub, no remote, loading, link click does not expand)
- [x] 4.3 Add the "Open project" link to `web/src/components/projects/ProjectDetailPanel.tsx`, left of "Delete project", shown on remote devices too and hidden without a remote; verify with `ProjectDetailPanel.test.tsx`
- [x] 4.4 Update `wiki/Frontend-Projects.md` for the new columns and button; verify with `cd api; python check_docs.py`

## 5. Integration

- [x] 5.1 Run `cd api; pytest`, `cd web; npm test` and `cd web; npm run build`; all pass with no type errors
- [x] 5.2 In the running app (`.\Start-Ledger.ps1`), confirm the-ledger and the-toolbox show GitHub with real counts, a project with no remote shows `--`, Source and Open project open the repo, and the table renders before the counts arrive; resize the window to check the narrow layout

## Workflow follow-up

- Archive the change after review; the wiki pages above are already updated by then.
