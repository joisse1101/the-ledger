## 1. Durable history store foundation

- [x] 1.1 In `claude_db.py`, add `history_db_path()` (`api/.history/history.db`) and schema setup for
      a `transcripts` table matching `ledger.db`'s columns; verify by running it once and confirming
      the file and table exist (`sqlite3 api/.history/history.db ".schema transcripts"`).
- [x] 1.2 Add an upsert function (`INSERT ... ON CONFLICT(session_id) DO UPDATE SET ...`) for
      writing scanned transcript rows into `history.db`; verify with a unit test that upserting the
      same `session_id` twice with different values leaves exactly one row with the latest values.
- [x] 1.3 Add a fetch function returning every row from `history.db`'s `transcripts` table; verify
      with a unit test against a small fixture db.

## 2. Merge into live reads

- [x] 2.1 Change `claude_db.fetch_transcripts()` to merge live `ledger.db` rows with `history.db`
      rows by `session_id`, preferring the live row on conflict; verify with a unit test: a
      session present only in history appears in the merged output, and a session present in both
      returns the live row's field values.
- [x] 2.2 Confirm `claude_transcripts.load_transcripts()`, `overview_stats.py`, and
      `transcript_query.py` need no code changes; verify by extending `test_overview_stats.py` and
      `test_transcript_query.py` with a case that includes a history-only (no longer on-disk)
      session and asserting it's counted/listed correctly with existing, unmodified code.

## 3. Delete propagation

- [x] 3.1 Extend the session-delete path so deleting a transcript also removes its row from
      `history.db`, including a session known only from `history.db` (already pruned from disk and
      absent from `ledger.db`) - the existence check backing `DELETE /api/sessions/{id}`'s 404 must
      recognize it as known, and the delete itself must tolerate the file already being gone rather
      than failing; verify with unit tests: (a) after deleting a session present in both stores, its
      `session_id` is absent from both the merged `fetch_transcripts()` output and a raw fetch of
      `history.db`; (b) deleting a history-only session succeeds (no 404/500) and purges its
      `history.db` row.
- [x] 3.2 Extend the project-delete path (`delete_transcript_rows_by_project`) to remove that
      project's rows from `history.db` too, using the same on-disk-folder matching the live path
      already uses; verify with a unit test covering a project that has sessions in `history.db`
      only (already pruned from disk and from `ledger.db`).

## 4. Standalone backup script

- [x] 4.1 Add `api/backup_history.py`: scans Claude Code's on-disk data (reusing `claude_db`'s
      existing scan/`refresh()`) and upserts the results into `history.db`, with no dependency on
      `server.py` running; verify by running `python api/backup_history.py` directly while the
      server is stopped and confirming `history.db` is created/updated.
- [x] 4.2 Verify the script is safe to run repeatedly without growing row counts for unchanged
      sessions; verify with a unit test invoking the backup logic twice in a row and asserting row
      counts are unchanged on the second run.

## 5. Config and documentation

- [x] 5.1 Add `api/.history/` to `.gitignore`; verify `git status` shows no untracked files after
      running the backup script locally.
- [x] 5.2 Update `CLAUDE.md`'s Data layer / Architecture sections to document `history.db`, the
      merge behavior, delete propagation, and `backup_history.py`, at the same depth as the
      existing `claude_db.py` documentation; verify by re-reading the section against the shipped
      behavior for accuracy.
- [x] 5.3 Document the Windows Task Scheduler setup (program `api\.venv\Scripts\python.exe`,
      argument `api\backup_history.py`, "Start in" `api\`, run as the logged-in user without
      elevation, daily trigger) in `CLAUDE.md` or `README.md`; verify by following the written
      steps once to create the task successfully.

## 6. Tests

- [x] 6.1 In `api/tests/test_claude_db.py`, add coverage for history schema creation, upsert
      idempotency, live-wins merge precedence, and delete propagation (single session and whole
      project); verify `pytest` passes.
- [x] 6.2 Add `api/tests/test_backup_history.py` covering the backup script's logic run in
      isolation (mirroring the `isolated_db` fixture pattern) without the server running; verify
      `pytest` passes.
- [x] 6.3 Extend `api/tests/test_api_data.py` with a case where a history-only (pruned) session is
      present, confirming it's reflected in `/api/overview` and `/api/transcripts` responses;
      verify `pytest` passes.

## 7. Manual verification

- [ ] 7.1 Create the Task Scheduler entry, by hand per the documented steps (task 5.3), and manually trigger a run; verify
      `history.db`'s row count/contents update as expected, inspected via the `sqlite3` CLI before
      and after.

## 8. Scripted installer for the scheduled task

- [x] 8.1 Add `api/Install-HistoryBackupTask.ps1`: registers/updates a Windows Scheduled Task
      running `api\.venv\Scripts\python.exe backup_history.py` daily, "Start in" `api\`, as the
      logged-in user with no elevation (`Interactive` logon, `Limited` run level); `-Uninstall`
      removes it; idempotent re-runs update the existing task rather than duplicating it.
- [x] 8.2 Add an `-InstallBackupTask` switch to the root `Start-Ledger.ps1` that invokes the
      installer script as part of normal startup, so installing the task and starting the app can
      be one command.
- [x] 8.3 Document the script (as the recommended path, manual GUI steps kept as a fallback) in
      `CLAUDE.md`'s "Setup & Run", and add a matching user-facing section to `README.md`, which
      previously didn't mention `history.db`/`backup_history.py`/the scheduled task at all.
