# Design

## Context

See proposal.md - Why. `GET /api/projects` is a fast read of the SQLite snapshot, and the Projects
list renders straight from it. The backend already shells out through injected `run` callables in
`app/infra/` (tests pass fakes), and its layers only import downward: `routers` -> `services` ->
`repositories` / `domain` -> `core`, with `infra` wrapping the OS. `gh` is installed and signed in on
the host; `git` is already required.

## Goals / Non-Goals

**Goals:**
- Resolve each project's remote and, for GitHub, its open issue and PR counts without slowing the
  Projects page or failing it when anything goes wrong.
- One place that turns a git remote into a web URL.

**Non-Goals:**
- Other trackers (Jira, Linear) and non-GitHub counts (GitLab and so on).
- Any write to a repo, or any use of the GitHub token outside the `gh` process on the host.
- A manual refresh control for the counts; the cache expiring is enough.

## Decisions

**A separate endpoint, `GET /api/projects/repos`, not new fields on `/api/projects`.**
It returns one entry per known project: `{path, host, url, issues, prs}`, each of the last four
nullable. The frontend merges by `path`. This keeps `/api/projects` additive-free and fast, lets the
table render first, and keeps the existing types unchanged. Alternative: extend each project row.
Rejected because every page load would wait on N network calls, and a slow `gh` would block the
Delete button and the charts.

**The endpoint takes no parameters.** It iterates `claude_projects.load_projects()`, so a request
cannot name a path (the "known project paths only" requirement). Same rule as `get_session`.

**Layers.**
- `app/core/remote_url.py` (pure): `web_url(remote) -> Optional[str]` and `host_label(url)`.
  Handles `git@host:o/r.git`, `ssh://git@host/o/r.git` and `https://[user@]host/o/r.git`; strips
  credentials and `.git`; returns None for anything that is not an http(s) or ssh-style remote
  (local paths, `file://`). `github.com` -> "GitHub", any other host -> the hostname.
- `app/infra/repo_cli.py`: `RepoCli(run=subprocess.run)` with `remote_url(path)` (`git -C <path>
  remote get-url origin`) and `open_counts(path)` (`gh issue list` and `gh pr list`, each
  `--state open --json number --limit 1000`, counted from the JSON). Both use `timeout`, no console
  window (`NO_WINDOW` as in `remote_system.py`), and return None on a non-zero exit, a timeout, an
  `OSError` (missing binary) or unparseable output. The reason is logged as a key/value line with the
  project path; it is not swallowed silently, only not raised.
- `app/services/project_repo_service.py`: for each known project, resolve remote -> url/host; only
  when the host is GitHub, fetch counts. Projects are looked up in a small thread pool (the calls
  are I/O-bound) and the result is cached per path with a TTL (5 minutes).
- `app/routers/projects.py`: a thin GET handler. `app/schemas/projects.py`: the item shape.

**Counts come from `gh issue list` / `gh pr list` run with the project folder as cwd**, so `gh`
resolves the repo from the remote itself and no owner/name parsing is needed for it. Alternative:
`gh api repos/o/r` `open_issues_count`. Rejected: it includes pull requests in the issue count, so it
cannot give the two separate numbers.

**Cache.** An in-process dict `{path: (expires_at, entry)}` in the service, TTL a constant. Failures
are cached for a shorter time so a transient `gh` outage heals quickly but a signed-out `gh` does not
get hammered on every poll. The clock is injected for tests. Alternative: cache on disk. Rejected;
the data is cheap to refetch and a stale on-disk value would outlive a `gh auth login`.

**Frontend.** `useProjectRepos()` in `web/src/api/queries.ts` (via `apiFetch`, relative path) with
`staleTime` matching the server TTL. `ProjectsList` adds three columns through the existing
`ResponsiveList` `ListColumn`s, joining `useProjectRepos().data` to rows by path. Source renders an
`<a target="_blank" rel="noopener noreferrer">`; a click on it must not also toggle the row, so it
stops propagation. `ProjectDetailPanel` renders an "Open project" anchor styled as the Delete
button's sibling, before it, outside the `is_local` condition. Types are added to `types.ts` in the
same change as the schema.

## Risks / Trade-offs

- **`--limit 1000` caps the count** -> A repo with more open items shows 1000. Acceptable here; the
  alternative is paginating GraphQL for a number nobody reads exactly.
- **First load after the cache expires is slow for many projects** -> Parallel lookups with a
  per-call timeout bound it, and the table never waits on it.
- **A signed-in `gh` account without access to a private repo** -> `gh` exits non-zero, so the cells
  show `--` and the link still works.
- **`gh` runs as the host user's account on a request from a LAN device** -> It only reads counts for
  repos the user already registered as projects, returns numbers rather than anything token-bearing,
  and the endpoint sits behind the same auth as the rest of `/api`.
- **Worktrees of a repo are not projects** -> No special handling; each project is one folder.

## Open Questions

- Exact visual treatment of the neutral label for non-GitHub hosts (hostname text vs an icon);
  decided while building, without changing the specs.
