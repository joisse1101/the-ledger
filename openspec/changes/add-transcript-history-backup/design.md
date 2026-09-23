## Context

See proposal.md - Why.

`claude_db.py` is the single SQLite-backed store `claude_projects.py`/`claude_transcripts.py` read
from. `refresh()` scans `~/.claude.json` and `~/.claude/projects/*/*.jsonl` and does a full
`DELETE FROM transcripts` + re-`INSERT` on every call (`api/claude_db.py:464-531`); `startup()`
deletes `ledger.db` (and its `-wal`/`-shm` files) on every process start and registers an `atexit`
hook to delete it again on exit (`claude_db.py:546-560`) - it is documented and relied on elsewhere
as a pure, disposable, rebuild-from-disk cache. `fetch_transcripts()` (`claude_db.py:578-583`) is
the one place that reads the `transcripts` table back out; `claude_transcripts.load_transcripts()`
(`claude_transcripts.py:60-62`) just wraps it row-for-row into `ClaudeTranscript` via
`_row_to_transcript()`, which reads fields with `row["field"]` - true of both `sqlite3.Row` and
plain `dict`. `overview_stats.py` and `transcript_query.py` both consume `load_transcripts()`'s
output and have no disk/SQL access of their own.

## Goals / Non-Goals

**Goals:**
- Session transcript summary data (not the raw `.jsonl`) survives Claude Code pruning the source
  file, and keeps contributing to Overview/Projects/the All list afterward.
- The backup can run without `server.py` running at all.
- No changes required in `overview_stats.py`, `transcript_query.py`, or `web/`.

**Non-Goals:**
- Preserving the `projects` table's history (out of scope per proposal.md - not at risk from
  Claude Code's cleanup, since it comes from `~/.claude.json`, not the pruned `.jsonl` files).
- Preserving raw transcript content/readability for a pruned session - the existing "conversation
  record can't be read" fallback (`web-dashboard` capability, session detail requirement) already
  covers this and needs no change.
- Making `ledger.db` itself durable (Option A from exploration) - kept fully disposable as today.

## Decisions

### A second, never-deleted SQLite file, not a CSV

`api/.history/history.db` (new directory, sibling to `api/.ledger/`) holds one `transcripts` table
with the same columns as `ledger.db`'s. Unlike `.ledger/`, nothing ever deletes this file or its
rows - no `atexit` hook, no wipe-and-rebuild in `startup()`.

Chosen over CSV because: this data is now read on every live Overview/Projects/All-list request
(many reads, one write/day), which is SQLite's shape, not a flat file's; typed columns (`cost
REAL`, `context INTEGER` nullable) avoid re-deriving casts on every read; `INSERT ... ON CONFLICT
DO UPDATE` gives an atomic per-row upsert instead of a whole-file read-modify-write; and it reuses
`claude_db.py`'s existing `_connect()`/`_ensure_schema()`/WAL patterns almost verbatim instead of
writing new file-parsing code.

Naming it `.history/` (not reusing `.ledger/`) keeps the disposable-cache-vs-durable-store
distinction visible in the filesystem, matching how `claude_sessions.py`/`claude_context.py`
already deliberately bypass `claude_db.py` for their own different freshness needs.

### Upsert keyed by `session_id`, live always wins on merge

`history.db`'s `transcripts` table has the same `session_id TEXT PRIMARY KEY` shape as
`ledger.db`'s. The backup script upserts every currently-scanned row
(`INSERT ... ON CONFLICT(session_id) DO UPDATE SET ...`), so a still-growing session's numbers get
overwritten in place on each run rather than duplicated.

`claude_db.fetch_transcripts()` changes to merge `ledger.db`'s live rows with `history.db`'s rows
by `session_id`, preferring the live row whenever both exist. Live-wins was chosen (over treating
history as immutable) because a session can still be active and growing at merge time, and because
it self-heals if a bad row were ever archived - the next live scan simply overwrites it. Merging
here, inside `claude_db.py`, means `claude_transcripts.py`, `overview_stats.py`, and
`transcript_query.py` need zero changes - they already just consume `fetch_transcripts()`'s output,
and a plain `dict` row satisfies `_row_to_transcript()`'s `row["field"]` access exactly like a
`sqlite3.Row` does.

### Delete flows purge history too

`claude_transcripts.delete_transcript()` and `delete_project_transcripts()` currently remove the
on-disk file and the matching `ledger.db` row(s) only (`claude_db.delete_transcript_row`,
`delete_transcript_rows_by_project`). Without a matching purge in `history.db`, a session the user
explicitly deleted would reappear on the very next merged read - directly breaking the existing
`web-dashboard` requirement that a deleted session disappears from the All list and stays gone.
Both delete paths gain an equivalent history-side delete, using the same folder-matching approach
`transcript_paths_for_project`/`delete_transcript_rows_by_project` already use (history rows carry
the same `path`/`cwd` columns).

### Backup script is standalone, reuses `claude_db`'s existing scan

`api/backup_history.py` calls `claude_db.refresh()` (or the lower-level `_scan_projects`/
`_scan_transcripts` it's built from) to get a fresh scan, then upserts the resulting transcript
rows into `history.db`. It needs no server process running - same precedent as
`api/gateway_signin.py`, already a standalone script that reuses `claude_db`-adjacent code outside
the FastAPI app. Running it touches `ledger.db` (via `refresh()`) the same way the app's own
refresh cycle does; the existing WAL mode + busy-timeout in `_connect()` already exist to let
concurrent readers/writers of `ledger.db` coexist, so running the script while `server.py` is also
running is safe without new locking.

### Triggering: OS-level Task Scheduler, not the app's own refresh loop

The daily trigger is an external Windows Task Scheduler entry invoking
`api\.venv\Scripts\python.exe api\backup_history.py` with "Start in" set to `api\`, run as the
logged-in user (no elevation, no `SYSTEM` account - every file involved is already owned by that
user). This is deliberately decoupled from `server.py`'s own 10-minute `refresh_loop()`, which only
runs while the app is open; per CLAUDE.md this isn't meant to be an always-on daemon, so a trigger
tied to the app's uptime could miss the backup entirely for weeks at a time. Daily cadence gives
large margin under Claude Code's typical multi-week retention default.

## Risks / Trade-offs

- [`history.db` grows without bound, forever] → Acceptable at this data's scale (one row per
  session, a few hundred bytes each); no pruning planned.
- [Schema drift between `ledger.db` and `history.db` as columns are added later] → Both schemas
  live in the same `_ensure_schema`-style function in `claude_db.py`, changed together; existing
  rows get the new column's default via `ALTER TABLE ... ADD COLUMN`.
- [Task Scheduler entry silently stops firing (missed run while asleep, task disabled, etc.)] →
  Daily cadence against a multi-week retention window leaves slack for several missed runs before
  any data is actually at risk; no in-app monitoring of the task's own health is planned.
- [A session deleted from `history.db` by the delete-purge path but not yet re-scanned into
  `ledger.db`'s history disappears from the All list before the corresponding on-disk delete
  finishes] → Same ordering the app already relies on for `ledger.db` deletes today; not a new
  risk this change introduces.

## Migration Plan

No data migration - `history.db` starts empty and accumulates from the first backup run onward.
Sessions already pruned from disk before this change ships are not recoverable; only new pruning
going forward is covered. Rollback is deleting `api/.history/` and reverting the merge in
`claude_db.fetch_transcripts()` - `ledger.db`'s own behavior is unchanged either way.
