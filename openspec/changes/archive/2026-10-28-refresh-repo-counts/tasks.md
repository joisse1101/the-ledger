# Tasks

## 1. Server drops cached repo lookups on refresh

- [x] 1.1 Add a cache clear to `ProjectRepoLookup` and a `clear_cache()` on `project_repo_service`; verify `test_clearing_the_cache_reads_a_fresh_lookup_at_once` passes
- [x] 1.2 Call `clear_cache()` from `POST /api/refresh` before the rescan; verify `test_refresh_endpoint_drops_the_cached_repo_lookups` passes and `cd api; pytest` is green
- [x] 1.3 Add the cache drop to the `POST /api/refresh` row in `wiki/Backend-API-Routes.md`; verify `cd api; python check_docs.py` passes

## 2. Refresh control re-reads counts and stays busy until they load

- [x] 2.1 Invalidate the project-repos query in `useRefresh` and update the control's tooltip and doc comment; verify the test that the repos query is marked stale after a refresh passes
- [x] 2.2 Make `useRefresh`'s `onSuccess` return the repos invalidation promise so the mutation stays pending until the refetch settles; verify a test shows `isPending` stays true while `/api/projects/repos` is outstanding, then clears
- [x] 2.3 Test that a repos response with null counts still ends in success (no `Refresh failed`), and that with no mounted repos query the mutation settles without requesting `/api/projects/repos`; verify `cd web; npm test` is green
- [x] 2.4 Add a sentence on the refresh behavior (cache drop, spinner held on the Projects page) to `wiki/Frontend-Api-Layer.md`; verify `cd api; python check_docs.py` passes
- [x] 2.5 Run `cd web; npm run build` and confirm it type-checks

## 3. Integration check

- [x] 3.1 With `.\Start-Ledger.ps1`, open Projects, change an issue count on GitHub, click refresh, and confirm the spinner holds until the count updates; then sign out of `gh` and confirm refresh still succeeds with `--` in the cells

## Workflow follow-up

- Archive the change after review so the two delta specs merge into `web-dashboard` and `project-repo-info`.
