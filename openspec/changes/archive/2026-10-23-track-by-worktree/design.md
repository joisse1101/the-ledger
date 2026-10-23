## Context

See proposal.md for motivation. Facts about the current code that shape the approach:

- A transcript's `project` is chosen in `scanner._scan_transcript_file`: the project matched from
  `~/.claude.json` by the transcript's on-disk folder, else `Path(cwd).name`. A worktree's folder is not
  in `~/.claude.json`'s project list, so it falls through to the `cwd` basename. That is why one worktree
  shows up as `add-wiki-docs`, `api` and `the-ledger`. The Projects page itself lists only
  `~/.claude.json` entries, so it shows no fake rows; the damage is in the `project` column.
- Membership of a project is decided in three places, all by the transcript's folder name
  (`sanitize_project_path(project)`): `overview_stats.filter_by_project`,
  `queries.transcript_paths_for_project` and `queries._delete_transcript_rows_by_project_in`.
- `git_branch` is the last `gitBranch` in the transcript; `cwd` is the last `cwd`.
- `transcripts` exists in `ledger.db` (rebuilt every start) and `history.db` (durable, never recreated).
  `connection.ensure_history_schema` adds new columns to `history.db` with swallowed `ALTER TABLE`s.
  `history.upsert_history_transcripts` re-writes a row only when its transcript is still on disk.
- `GROUP_KEYS` maps a `group_by` name to a key function; `group_totals` keeps the top 7 and folds the
  rest into "Other". The frontend colours groups from the API's `group_order`.
- `api/tests/test_layers.py` lets `repositories` and `domain` import `core`, and nothing sideways.

## Goals / Non-Goals

**Goals:**
- One place that knows what a Claude Code worktree path looks like, used by the scan, the project
  filter and the delete.
- The project panel groups by "worktree, else branch" with no new chart components.
- Existing data, including sessions already pruned from disk, is corrected without user action.

**Non-Goals:**
- Worktrees created by plain `git worktree add` elsewhere on disk; no git subprocess runs.
- A branch/worktree toggle. Both keys come from stored columns, so one can be added later without a
  data change.
- Grouping Overview's per-project donut by worktree. Overview stays per project.
- Splitting the hourly activity chart by work stream.

## Decisions

### D1: The path rule is a pure function in `app/core/worktrees.py`

`parse_worktree(cwd: str) -> Optional[Worktree]` normalises backslashes to `/` and matches
`^(?P<repo>.+?)/\.claude/worktrees/(?P<name>[^/]+)(?:/|$)`, returning `Worktree(repo_root, name)` or
`None`. Matching the first `/.claude/worktrees/` keeps the repo root as the shortest prefix, so a
repo that itself lives under a worktree folder resolves to the outermost one.

- Why `core`: `repositories` (scanner, queries) and `domain` (filter) both need it, and `test_layers.py`
  only lets them share `core`.
- Alternative: parse the transcript folder name. Rejected; `sanitize_project_path` turns every
  non-alphanumeric into `-`, so `-claude-worktrees-` cannot be split back into repo and name safely.
- Alternative: ask git (`rev-parse --git-common-dir`). Rejected by scope: only Claude Code's own
  worktrees, and a deleted worktree has no repo to ask.

### D2: Detect from the first `cwd` in the transcript, not the last

The scanner already keeps the last `cwd` (and `git_branch`). For worktree detection it uses the first
`cwd` seen, which is where the session started; a session that later `cd`s out of the worktree, or into
a subfolder, is still that worktree's. `cwd` keeps its current "last seen" meaning for everything else.
A resumed session that started in a worktree stays in it.

### D3: Store `worktree` and fix `project` at scan time; derive the parent folder when filtering

New `transcripts.worktree TEXT NOT NULL DEFAULT ''`. For a worktree session the scanner sets
`worktree = name` and `project = Path(repo_root).name`. No `project_folder` column is added: the
parent repo's folder is derived, not stored. The stored `cwd` is the *last* one while detection uses the
*first* (D2), so a session that `cd`'d out of its worktree cannot be resolved from `cwd` alone. Instead the
rule strips the sanitized suffix `sanitize_project_path("/.claude/worktrees/<name>")` from the transcript's own
folder name (`paths.project_folder`), falling back to the parsed `cwd`'s repo root, then to the folder itself.
`ClaudeTranscript` gets one derived helper, `project_folder`, returning that for a worktree session and
`path.parent.name` otherwise.

- All three membership sites (overview filter, `transcript_paths_for_project`, row delete) use that one
  rule instead of `path.parent.name`, so view and delete cannot disagree.
- Why derive instead of store: nothing to backfill for the folder, and it works for history-only rows.
- Trade-off: the delete queries now parse `cwd` per row in Python (they already load every row to
  compare folder names), so no extra cost class.

### D4: Migration of `history.db` is a startup pass over its rows

`ensure_history_schema` gains `ALTER TABLE transcripts ADD COLUMN worktree TEXT NOT NULL DEFAULT ''`
(same swallow-duplicate pattern as its siblings). A following idempotent pass selects rows where
`worktree = ''` and `cwd` parses as a worktree, then sets `worktree` and `project`. It runs on the stored
`cwd`, so rows whose files were pruned are corrected too, and a second run finds nothing to do.
`ledger.db` needs none of this: it is rebuilt from the scan on every start.

- Alternative: only fix rows on the next backup upsert. Rejected; a pruned session is never re-upserted,
  so it would stay wrong forever.

### D5: Work stream is a new `group_by` value, not a change to `branch`

`GROUP_KEYS["worktree"]` returns `f"wt {t.worktree}"` when set, else `t.git_branch or NO_BRANCH`.
`"branch"` keeps its meaning, so the API change is additive and the existing `group_by=branch` callers
are untouched. `ProjectDetailPanel` switches to `groupBy: "worktree"`. `group_totals`, the 7-slice cap and
`group_order` colouring work unchanged. The API value is `worktree` (what the key mostly distinguishes);
the chart wording is "branch / worktree".

- The `wt ` prefix is the collision guard: git ref names may legally contain spaces nowhere, so
  `wt <name>` cannot equal a branch name.

### D6: Summary gains `worktrees`; `branches` is unchanged

`summary()` already returns `branches`. It adds `worktrees`: the count of distinct non-empty
`t.worktree`. `branches` keeps counting `GROUP_KEYS["branch"]` values, so a project with two
worktrees still reports their `worktree-<name>` branches there; the two figures describe different
things and the UI shows both.

### D7: All list: new field, filter and column

`transcript_item` adds `worktree`; `/api/transcripts` accepts repeated `worktree` and `sort=worktree`;
the options payload adds `worktrees` (distinct non-empty names). The web `AllList` adds a Worktree
column and a `FilterMultiselect`. Empty worktree renders as `--` through the existing `formatText`.

### D8: Deleting a project deletes its worktree sessions

Project delete today removes the folder(s) holding the project's transcripts. With D3 a project's
sessions include worktree sessions, whose transcripts sit in other `~/.claude/projects/` folders.
Deleting only the repo's own folder would leave sessions the spec says must no longer appear, still
attributed to a project that is gone. So delete removes every folder that holds a member transcript.

- Risk: this removes more on-disk data than before. The confirmation modal already says "remove all of its
  on-disk session transcripts"; its text is left alone because worktree sessions are the project's.
- Alternative: leave worktree folders and drop them from attribution. Rejected; it turns them back into
  fake projects after the repo is deleted.
- A shared folder is only removed when it holds nothing but member transcripts (a worktree folder is
  specific to that worktree, so this holds).

## Risks / Trade-offs

- [A worktree deleted from disk, with a repo path moved or renamed] → its sessions keep the `cwd`
  recorded at the time, so they stay attributed to the old repo path; they fold into a project that may
  no longer exist in `~/.claude.json`. Acceptable; same failure as any moved project today.
- [Many short-lived worktrees crowd the top 7 and fold into "Other"] → The time-range selector narrows
  this; the cap is not changed.
- [One feature split across a worktree move shows as two entries] → Intended by the supersede rule and
  accepted; a toggle is the later escape hatch (non-goal).
- [Claude Code changes its worktree folder] → The rule is one constant in `core`; a test pins the
  current layout, and a changed layout falls back to today's behaviour (sessions appear under the
  worktree name), not an error.
- [First-`cwd` rule misreads a session that started elsewhere and `cd`'d into a worktree] → such a
  session is not attributed to the worktree; Claude Code's own `--worktree` starts the session inside
  it, so this is the uncommon case.
- [Per-row `cwd` parsing in delete and filter] → Pure string work over rows already loaded; no
  measurable cost at this scale.

## Migration Plan

1. Ship the code. On first start `history.db` gains the column and the correction pass runs; `ledger.db`
   is rebuilt by the scan, so both stores agree after one start.
2. Rollback: the extra column is ignored by older code (inserts name their columns), and the corrected
   `project` values stay valid for it. No destructive step is taken by the migration.
3. Project delete behaviour changes with the code and needs no migration.
