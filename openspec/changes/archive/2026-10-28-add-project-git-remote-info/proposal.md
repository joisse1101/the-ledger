# Proposal

## Why

The Projects page shows what Claude has done in each project but nothing about the project's repo on
its host. To see how many issues or pull requests are waiting, or to reach the repo, the user has to
leave the dashboard and find the project by hand. Each project's git remote already says where it
lives, and the `gh` CLI is installed and signed in on the host.

## What Changes

- The Projects list gains a **Source** column (the host, "GitHub" for a GitHub remote), an **Issues**
  column and a **PRs** column holding the repo's open issue and open pull request counts.
- The Source label links to the remote's web page.
- The selected project's panel gains an **Open project** button, placed to the left of "Delete
  project", that opens the same web page. It is a plain link, so it works from other devices too.
- A project that is not a git repo, has no remote, or has a non-GitHub remote shows `--` for the
  counts. A non-GitHub remote keeps its link and a neutral Source label; no remote means no link and
  no button.
- The backend resolves the remote with `git` and reads counts with `gh`. The lookup is separate from
  `GET /api/projects` and cached, so the table never waits on the network.
- `gh` becomes a soft dependency: when it is missing, signed out, offline or rate-limited the counts
  show `--` and nothing else is affected.

No tickets column: GitHub issues are the tickets, and no other tracker is in scope.

## Capabilities

### New Capabilities
- `project-repo-info`: each project's git remote, its host label and web link, and its open issue and
  pull request counts, with the graceful-fallback rules and the Open project button.

### Modified Capabilities

None. The existing Projects page requirements are unchanged; the new requirements sit beside them.

## Impact

- **Backend (`api/`)**: a new `infra` wrapper around `git` and `gh`, a service and a router for the
  lookup, and a schema for its JSON. Paths come only from `~/.claude.json` project entries, never
  from a request value. No change to `GET /api/projects` or the delete route.
- **Frontend (`web/`)**: `ProjectsList` columns, `ProjectDetailPanel` button, a query hook and the
  matching types in `web/src/api/types.ts`.
- **Dependencies**: `gh` (GitHub CLI, signed in with `gh auth login`) as an optional host tool;
  `git` is already required.
- **Docs**: `wiki/Setup-And-Run.md`, `wiki/Backend-API-Routes.md`, `wiki/Frontend-Projects.md`.
