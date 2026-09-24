## Why

Claude Code prunes old session transcripts from `~/.claude/projects/*/*.jsonl` on its own
retention schedule. The Ledger's `ledger.db` is a pure derived cache — every `refresh()` fully
replaces the `transcripts` table with whatever is currently on disk — so a pruned session's row
disappears from Overview and the Sessions page's All list at the same moment, permanently. There
is currently no way to see historical usage older than Claude Code's own retention window.

## What Changes

- Add a durable, never-wiped history store (separate from the disposable `ledger.db` cache) that
  retains a summary row per session transcript ever scanned, so a session's row survives after its
  `.jsonl` file is pruned from disk.
- Add a standalone backup script that scans Claude Code's on-disk data and upserts into the
  history store, runnable independently of `server.py` (no running API server required), intended
  to be triggered daily by an OS-level scheduled task (e.g. Windows Task Scheduler) so it keeps
  capturing data even when the app itself isn't running.
- `claude_db.py`'s transcript reads merge live `ledger.db` rows with the history store by
  `session_id`, preferring the live row when a session exists in both (it's the fresher scan) —
  Overview, Projects, and the Sessions page's All list all consume this merged view transparently,
  with no changes needed in `overview_stats.py`, `transcript_query.py`, or the frontend.
- Deleting a session (or a project's transcripts) through the existing delete flows also removes
  the matching row(s) from the history store, so an explicitly deleted session doesn't reappear on
  a later read.
- Scope: this covers `transcripts` only. The `projects` table (from `~/.claude.json`) already only
  ever reflects each project's *last* session and isn't pruned by Claude Code's retention cleanup,
  so it isn't part of this change.

## Capabilities

### New Capabilities

- `transcript-history`: durable retention of session transcript summary rows beyond Claude Code's
  own on-disk retention window, via a daily-scheduled backup and a live+history merge on read.

### Modified Capabilities

- `web-dashboard`: the Sessions page's All list currently requires showing "every session
  transcript on disk" — this changes to also include sessions preserved in the history store after
  their on-disk file has been pruned.

## Impact

- `api/claude_db.py`: new durable history storage (schema, upsert, fetch) and a merge step in the
  transcript read path; delete paths extended to also purge history rows.
- New `api/backup_history.py`: standalone script for the scheduled task.
- `.gitignore`: new durable-history file location.
- `openspec/specs/web-dashboard/spec.md`: delta to the All list requirement.
- Tests: `api/tests/test_claude_db.py` (merge/upsert/delete propagation), new
  `api/tests/test_backup_history.py`.
- No frontend changes — the merge is transparent to `web/`.
- Operational: a Windows Task Scheduler entry (documented in CLAUDE.md/README, not app code) is
  needed to actually trigger the daily backup; out of scope for the app itself to configure.
