# Design

## Context

Repo info is its own request, `GET /api/projects/repos`, served by `ProjectRepoLookup`, which caches each project's result for 5 minutes (60 seconds when incomplete). On the client it is the `project-repos` query with a matching 5-minute `staleTime`. `POST /api/refresh` only rescans the SQLite snapshot, and `useRefresh` only invalidates the queries derived from it. See proposal.md for the motivation.

## Goals / Non-Goals

**Goals:**
- A manual refresh gets counts that are fresh from `gh`, not from either cache.
- The refresh control stays busy until those counts have loaded.
- A failing `gh` never turns into a failed refresh.

**Non-Goals:**
- Making the server's refresh endpoint wait on `gh`; the rescan stays fast and the counts stay a separate request.
- `glab` / GitLab support.
- Clearing the repo cache on the 10-minute background rescan.

## Decisions

**Clear the server cache in the refresh route, not via a request parameter.** `POST /api/refresh` calls a `clear_cache` on the repo service before rescanning. The alternative was `GET /api/projects/repos?fresh=1`; it was rejected because the repos route deliberately takes no parameters (the folders git and `gh` run in must never come from a request), and the cache decision belongs with the action that means "refresh". Clearing before the rescan, not after, means a client that refetches as soon as the POST returns cannot hit a stale entry.

**Keep the counts a separate request and hold the spinner on the client.** `useRefresh`'s `onSuccess` returns the promise from `invalidateQueries` for the repos key alongside the existing keys, so the mutation stays pending until the refetch settles. The alternative was to fold the counts into `POST /api/refresh`; that would make the rescan as slow as the slowest `gh` call and break the rule that the Projects table never waits on `gh`.

**Failure stays inside the repos request.** The repos endpoint answers 200 with null counts when `gh` fails, and `invalidateQueries` does not reject when a refetch fails. So no new error handling is needed, and `Refresh failed` still means the rescan failed.

**Only mounted queries are awaited.** `invalidateQueries` refetches active queries and marks inactive ones stale. On a page that does not show counts the spinner therefore does not wait on `gh`, and the counts are fetched fresh (the server cache is already clear) when Projects is next opened. Forcing a refetch of inactive queries would run `gh` for every project on every refresh from any page.

## Risks / Trade-offs

- [A refresh on the Projects page takes as long as the slowest `gh` call, up to its 20-second timeout, across 4 workers] → The spinner is the only thing waiting; the table is already on screen, and the user asked for a full refresh.
- [Clearing the cache while a repos request is in flight can let that request write a pre-refresh result back into the cache] → The window is short and the client refetch that follows the refresh reads after the clear; the entry expires in 5 minutes at worst.
- [Repeated refreshing runs `gh` against GitHub each time] → Acceptable for a manual, single-user action; rate limiting already shows as `--`.
