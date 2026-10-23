## Why

Claude Code's own worktrees (`<repo>/.claude/worktrees/<name>`) are a normal way to split work off a
branch, but the dashboard cannot see them. Each worktree's transcripts are filed under their own
`~/.claude/projects/` folder, so a worktree session is named after the worktree (or after whatever
subfolder the session `cd`'d into) and shows up as a separate "project" (`add-wiki-docs`, `api`,
`the-ledger` for the same worktree). Usage per worktree cannot be told apart from the parent repo's,
and the project charts cannot show it.

## What Changes

- Detect a Claude Code worktree from a session's `cwd` (a path under `.claude/worktrees/<name>`) and
  record its name on the session. Git itself is never consulted, so only Claude Code's own worktrees
  are recognised.
- Attribute a worktree session to its parent repo's project: the project name, the Overview's
  per-project charts, the All list's Project filter and the Projects page's per-project charts all
  treat it as part of the repo it was split from. The fake `add-wiki-docs` / `api` project entries
  stop appearing.
- Group a project's charts by "work stream": `wt <name>` for a session in a worktree (the worktree
  supersedes the branch, even if the session switched branches inside it), otherwise its git branch
  (or "(no branch)"). The `wt ` prefix keeps a worktree label from colliding with a branch label.
  There is no branch/worktree toggle.
- Add a Worktrees figure beside Branches in the project panel's summary stats; the hourly activity
  chart stays aggregate.
- Show the worktree on the All sessions list as its own column, with a Worktree filter; the git branch
  stays on every row.
- Deleting a project also deletes the transcripts of its worktree sessions, so the project and its
  sessions are gone together.
- Existing `ledger.db` / `history.db` rows are corrected on the next scan or start, including sessions
  already pruned from disk.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-dashboard`: project membership of a worktree session; the project panel's charts group by work
  stream and gain a Worktrees figure; the All list gains a Worktree column and filter; project delete
  covers worktree sessions.
- `transcript-history`: the durable store carries each session's worktree, and rows preserved before
  this change are corrected without needing the transcript file.

## Impact

- `api/`: new path rule in `app/core/`; `repositories/db/` (scanner, snapshot, history upsert, schema
  and in-place migration, delete queries); `repositories/claude_transcripts.py`; `domain/overview_stats.py`
  (project filter, new group key, summary), `domain/transcript_query.py` (filter and options);
  `schemas/transcripts.py`, `routers/transcripts.py` and `services/overview_service.py` (new field,
  query parameter, group value). Additive JSON only: existing fields and `group_by=branch` keep their
  meaning.
- `web/`: `api/types.ts`, `api/queries.ts`, `components/overview/chartTheme.ts`,
  `projects/ProjectDetailPanel.tsx`, `projects/ProjectSummaryStats.tsx`, `sessions/AllList.tsx`.
- Docs: the wiki pages for the backend data layer, history store, API routes, overview and queries,
  and the Frontend Overview, Projects and Sessions pages.
- The in-flight `review-tracking` change does not touch these areas.
- Behaviour changes users will notice: project counts and per-project charts on Overview drop the fake
  worktree projects and fold their usage into the parent repo.
