## Why

Worktree tracking only recognises Claude Code's own layout, `<repo>/.claude/worktrees/<name>`. Worktrees
kept anywhere else in the repo, such as `<repo>/.trees/<name>`, are not seen as worktrees: each shows
up as a project of its own (`config-worktree-path` rather than `the-ledger`), and its usage is
missing from its repo's figures. The folder is a per-machine habit, so it needs to be set by the user,
not hardcoded.

## What Changes

- Add a Settings page with one global list of worktree folders, each a path relative to a repo root
  (for example `.trees`). A session that started in `<repo>/<folder>/<name>` counts as a worktree
  session of `<repo>` in every repo, exactly as a `.claude/worktrees` session does today.
- `.claude/worktrees` is built in: always on and never removable. User folders are added on top.
- Folder paths are validated: relative only, no `..`, no drive letter or leading `/`. Backslashes
  are normalised to `/`, and nested folders (`tools/wt`) are allowed.
- Saving takes effect at once: the snapshot is rescanned and preserved history rows with no worktree
  are re-attributed, so earlier sessions in a newly added folder move under their repo without a
  restart.
- Removing a folder fully undoes it: every session in that folder, whether its transcript is still on
  disk or only preserved in history, goes back to being a project of its own. The list always
  reflects what is configured now, so adding and removing a folder are exact opposites.
- The Settings page and its endpoints are for the machine running the app only. The navigation shows
  Settings only to a browser on that machine, and the server refuses any settings request that is not
  local, even when it carries a valid access token. The desktop widget gets no settings.
- The list is stored in a gitignored file under `api/.ledger/`.

## Capabilities

### New Capabilities

- `dashboard-settings`: the local-only Settings page and endpoints, the worktree-folder list (built-in
  entry, validation, persistence), and the rule that the list defines what counts as a worktree.

### Modified Capabilities

- `transcript-history`: preserved rows are reconciled with the configured folders whenever the list
  is saved (not only at start), in both directions: rows gain a worktree when their folder is added
  and lose it when their folder is removed.

## Impact

- `api/`: `app/core/worktrees.py` matches the configured folders, not one hardcoded pattern;
  `repositories/db/paths.py` strips whichever folder matched; a new settings store, service and
  router (`GET`/`PUT /api/settings`, local only); the save path triggers a rescan and
  `correct_worktree_rows`.
- `web/`: a Settings page and route, a `localOnly` nav entry driven by `/api/meta`'s `is_local`, and
  the settings query and mutation in `api/`.
- Docs: wiki pages for the API routes, security, data layer, history store, and the frontend shell.
- Additive only: with no folders added, behaviour is unchanged. The in-flight `review-tracking` change
  does not touch these areas.
