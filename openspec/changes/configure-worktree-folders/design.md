## Context

See proposal.md for motivation. Today worktree recognition is one hardcoded regex in
`app/core/worktrees.py` (`<repo>/.claude/worktrees/<name>`), used in three places:

- `repositories/db/scanner.py` - sets a session's worktree and parent project from its first `cwd`.
- `repositories/db/history.py` `correct_worktree_rows` - fixes `history.db` rows with `worktree = ''`
  from their stored `cwd`; runs once at start from `snapshot.startup()`.
- `repositories/db/paths.py` `project_folder` - strips the sanitized `/.claude/worktrees/<name>`
  suffix from a transcript's `~/.claude/projects/` folder to find the repo's folder (used by project
  membership and delete).

Constraints: the layer rules in `tests/test_layers.py` (core imports nothing from `app`; repositories
import only core; routers only core/schemas/services). `backup_history.py` is a separate process that
scans through `repositories/db`, so it must see the same folder list as the server. Local-only
routes already follow one pattern: `is_local(request)` in the router, 403 otherwise.

## Goals / Non-Goals

**Goals:**
- One source for the folder list, read by the server and the backup script alike.
- Recognition stays a pure function in `core`, testable without files.
- Saving reconciles both stores (`ledger.db` by rescan, `history.db` by a two-way pass) before the
  response returns, so the next read is already correct.

**Non-Goals:**
- Asking git which worktrees exist. Detection stays path-based.
- Per-repo folders, or any setting beyond the worktree-folder list.
- Watching the settings file for hand edits while the app runs; a hand edit applies on the next
  start or save.

## Decisions

### The folder list is passed into `parse_worktree`
`parse_worktree(cwd, folders)` builds its match from `BUILT_IN_FOLDER` (`.claude/worktrees`) plus the
given folders: `^(?P<repo>.+?)/(?P<folder>f1|f2|...)/(?P<name>[^/]+)(?:/|$)`, each folder
`re.escape`d. The lazy `repo` group keeps the outermost repo, as today. `Worktree` gains `folder` so
`project_folder` knows which suffix to strip. Validation and normalisation (`normalize_folder`) live
beside it in `core`, as pure functions.

*Alternative:* a module-level list in `core` set at start. Rejected: hidden global state, and the
backup process would need its own wiring to set it.

### Settings live in a small JSON store under `repositories/`
`repositories/settings_store.py` reads and writes `api/.ledger/settings.json`
(`{"worktree_folders": [".trees"]}`, user folders only; the built-in is never stored). A missing or
unreadable file means no user folders, so behaviour falls back to today's. Writes go to a temp file
then `os.replace`, so a crash never leaves half a file. The path can be overridden by
`LEDGER_SETTINGS_PATH`, as `LEDGER_TRANSFER_DIR` does for the drop folder, which also lets tests
point it at `tmp_path`. `api/.ledger/` is already gitignored.

The scanner, `correct_worktree_rows` and `project_folder`'s callers load the list from the store at
the start of each scan or pass, then hand it to `core`. Because `backup_history.py` scans through the
same repository code, it picks the list up with no extra wiring.

*Alternative:* store the list in `history.db`. Rejected: it mixes configuration into the durable
transcript store, and that store's schema is migrated in place, which is heavier than a JSON file.

### `correct_worktree_rows` becomes a two-way reconcile
It selects every row (not only `worktree = ''`). A row with a stored worktree whose transcript folder
name still ends in a listed folder's sanitized `/<folder>/<worktree>` is kept as is: that folder is
fixed from where the session started, while the stored `cwd` is the last directory seen and may have
moved out of the worktree. Every other row compares `parse_worktree(cwd, folders)` with the stored
worktree:

```
match now?   stored worktree?   action
yes          same name          nothing
yes          none / different   set worktree = name, project = basename(repo)
no           yes                set worktree = '', project = stored worktree name
no           none               nothing
```

Reverting sets the project to the worktree's name, which is what the row held before tracking (the
worktree directory is the session's own `~/.claude/projects/` folder). The pass runs at start, as
today, and on every save. It is one transaction over `session_id, cwd, worktree`, and is
cheap at this app's history sizes.

### Saving runs validate, write, reconcile, rescan in order
`services/settings_service.py`:

```
PUT /api/settings  {worktree_folders: [...]}
   router: is_local? else 403
   service: normalize + validate each (400 with the reason on the first bad one; dedupe = 400)
            -> settings_store.write
            -> history.correct_worktree_rows()      (history.db, both directions)
            -> refresh.locked_refresh()             (rebuild ledger.db from disk)
   returns the saved list (built-in first, flagged)
```

`GET /api/settings` (also local-only) returns the same shape. The reconcile goes before the rescan
so the rescan's live rows, which take precedence on merge, land on already-reconciled history. Both
routes are reached only through the existing security middleware, so the CSRF header rule for `PUT`
applies unchanged.

### Frontend: a `localOnly` nav entry and a route guard
`Nav.tsx` gains `localOnly: true` on a Settings entry, filtered on `useMeta().data?.is_local`, next
to the existing `remoteOnly`. `SettingsPage` sends any non-local device to `/` (the same behaviour as
Files when Remote mode is off), so a pasted link shows the default page. The page lists the built-in
folder (no remove control), user folders each with Remove, and an input with Add. Every add or remove
saves at once and invalidates the queries that hold sessions, projects and overview data, so open
pages pick up the new attribution. Validation errors from the server show inline under the input.

## Risks / Trade-offs

- [A generic folder name such as `build` captures unrelated sessions under a repo] → names are
  matched only as a whole path segment directly under the repo, and removing the folder fully undoes
  it.
- [The reconcile's revert assumes the pre-tracking project was the worktree's name] → this is how
  the scanner names a session filed under its own folder; a session that started elsewhere and `cd`'d
  in was never a worktree session, so it is never reverted.
- [A save blocks on a full rescan] → same cost as the existing manual Refresh; the Add/Remove control
  shows a pending state until it returns.
- [Two folders where one is a prefix of another (`wt`, `wt/inner`)] → the alternation is ordered
  longest first, so the more specific folder wins.

## Migration Plan

None needed. With no settings file the list is just `.claude/worktrees`, and the reconcile then
matches today's start-up correction exactly (it only adds; nothing is in a removed folder).
Rollback: delete `api/.ledger/settings.json` and restart; `.trees` sessions revert on the start-up
reconcile.
