# Backend: history store

> Requirements live in `openspec/specs/transcript-history/spec.md`. This page describes how the code meets them, not what it must do.

  `claude_db.py` also owns a second, durable store at `history_db_path()` (`api/.history/history.db`,
  gitignored) holding the same `transcripts` table shape as `ledger.db`'s (shared via
  `_ensure_history_schema()`) — unlike `ledger.db`, nothing ever wipes this file or its rows: no
  `atexit` hook, no delete-and-reinsert in `refresh()`. `upsert_history_transcripts()` writes rows into
  it with `INSERT ... ON CONFLICT(session_id) DO UPDATE SET ...`, so re-backing-up a still-growing
  session overwrites its row in place rather than duplicating it; `fetch_history_transcripts()` reads
  every row back, including ones for sessions since pruned from disk. `fetch_transcripts()` (the one
  function `load_transcripts()` calls) merges `ledger.db`'s live rows with `history.db`'s rows by
  `session_id`, preferring the live row whenever a session exists in both since it's the fresher scan
  — this merge is the only thing that changed for callers; `claude_transcripts.py`, `overview_stats.py`
  and `transcript_query.py` need no changes of their own, since they already just consume
  `fetch_transcripts()`'s output. `delete_transcript_row()` and `delete_transcript_rows_by_project()`
  purge from both stores, so an explicitly deleted session or project doesn't reappear on a later
  merged read; `transcript_path_for_session()` falls back to `history.db` when a session isn't in
  `ledger.db`, so a history-only session (already pruned from disk and absent from `ledger.db`) is
  still recognized as known — and `claude_transcripts.delete_transcript()` treats its missing file
  (`unlink()`'s `FileNotFoundError`) as "already gone" rather than a failure, purging whichever store
  actually has the row.
- `api/backup_history.py` is a standalone script, runnable independently of `server.py` (no server
  process needed): it calls `claude_db._scan_projects()`/`_scan_transcripts()` directly — the same
  scan `refresh()` itself calls — and upserts the results straight into `history.db`, skipping
  `ledger.db` entirely. It's meant to be triggered daily by an OS-level scheduled task (see [Setup and run](Setup-And-Run.md)) so history keeps accumulating even when the app isn't running; safe to run repeatedly,
  since the upsert overwrites an unchanged session's row rather than growing it.
