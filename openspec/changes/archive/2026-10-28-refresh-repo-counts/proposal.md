# Proposal

## Why

The refresh button only rescans Claude Code's local files. A project's open issue and pull request counts are fetched when the Projects page loads and then reused for a few minutes, so the only way to see a newer count is to wait. One click on refresh should refresh everything the dashboard shows (GitHub issue #50).

## What Changes

- `POST /api/refresh` drops the cached repo lookups, so the next read of `GET /api/projects/repos` asks git and `gh` again instead of serving the cache.
- The refresh control refetches each project's repo info together with the rescanned session data, and its spinner stays on until that refetch has finished.
- A missing, signed-out, offline or rate-limited `gh` does not fail the refresh: the affected counts show `--`, as they already do, and the rest of the refresh completes.
- The refresh control's tooltip says it also refreshes issue and PR counts.
- No change to the automatic 10-minute rescan or to how often the counts refetch on page load.
- Out of scope: `glab` / GitLab. Counts stay GitHub-only; other hosts keep showing `--`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-dashboard`: the single refresh control also re-reads each project's issue and PR counts and holds its in-progress state until they have loaded; a count that cannot be read does not make the refresh fail.
- `project-repo-info`: counts are cached for a few minutes, except that a manual refresh bypasses the cache.

## Impact

- API: `api/app/routers/meta.py` (`POST /api/refresh`), `api/app/services/project_repo_service.py` (a cache clear). The response shape is unchanged.
- Web: `web/src/api/queries.ts` (`useRefresh`), `web/src/components/RefreshControl.tsx`.
- Tests: `api/tests/test_main.py`, `api/tests/services/test_project_repo_service.py`, `web/src/api/queries.test.tsx`.
- Docs: `wiki/Backend-API-Routes.md`, and the frontend wiki pages that describe the refresh control.
- Much of this is already in the working tree from the earlier #50 work; what remains is holding the spinner until the repos refetch settles.
