# Backend: history store

This page explains the durable history database, which keeps transcripts after Claude Code prunes them from disk, and the standalone script that fills it. The term is defined in the [Glossary](Glossary.md#history-store).

> Requirements live in `openspec/specs/transcript-history/spec.md`. This page describes how the code meets them, not what it must do.

## The store

### Where it lives

`api/app/repositories/db/` also owns a second, durable store at `history_db_path()`. The file is `api/.history/history.db` (gitignored). It holds the same `transcripts` table shape as `ledger.db`'s. `_ensure_history_schema()` shares that shape, and also adds the `worktree` column to an older file.

### It is never wiped

Unlike `ledger.db`, nothing ever wipes this file or its rows. There is no `atexit` hook. There is no delete-and-reinsert in `refresh()`.

## Writing and reading

### Writing

`upsert_history_transcripts()` writes rows with `INSERT ... ON CONFLICT(session_id) DO UPDATE SET ...`. So re-backing-up a still-growing session overwrites its row in place rather than duplicating it.

### Reading

`fetch_history_transcripts()` reads every row back, including ones for sessions since pruned from disk.

`fetch_transcripts()` is the one function `load_transcripts()` calls. It merges `ledger.db`'s live rows with `history.db`'s rows by `session_id`. It prefers the live row whenever a session exists in both, since it is the fresher scan.

This merge is the only thing that changed for callers. `claude_transcripts.py`, `overview_stats.py` and `transcript_query.py` need no changes of their own. They already just consume `fetch_transcripts()`'s output.

## Correcting worktree rows

`correct_worktree_rows()` runs at start from `startup()`, and after every Settings save. It reconciles every row, pruned sessions included, with the configured worktree folders, in both directions. It is idempotent.

It applies these rules in order:

- A row filed under a listed folder (its transcript folder's name) keeps its worktree.
- Otherwise, a row whose stored `cwd` is in a worktree gains it and its repo's project.
- Otherwise, a row whose worktree folder is no longer listed loses it and takes the worktree's name as its project.

## Deleting

`delete_transcript_row()` and `delete_transcript_rows_by_project()` purge from both stores. So an explicitly deleted session or project does not reappear on a later merged read.

`transcript_path_for_session()` falls back to `history.db` when a session is not in `ledger.db`. So a history-only session, already pruned from disk and absent from `ledger.db`, is still recognized as known.

`claude_transcripts.delete_transcript()` treats its missing file as "already gone" rather than a failure. The missing file shows up as `unlink()`'s `FileNotFoundError`. It purges whichever store actually has the row.

## `api/backup_history.py`

It is a standalone script, runnable independently of the backend. No server process is needed. It calls `scanner.scan_projects()` and `scan_transcripts()` directly, the same scan `refresh()` itself calls. It upserts the results straight into `history.db`. It skips `ledger.db` entirely.

It is meant to be triggered daily by an OS-level scheduled task. See [Setup and run](Setup-And-Run.md). So history keeps accumulating even when the app is not running.

It is safe to run repeatedly. The upsert overwrites an unchanged session's row rather than growing it.
