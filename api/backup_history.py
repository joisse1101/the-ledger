"""Standalone daily backup: scans Claude Code's on-disk data and upserts it into
`history.db`, Ledger's durable transcript store - see `openspec/changes/add-transcript-history-backup/`.

Meant to be triggered by an OS-level scheduled task (e.g. Windows Task Scheduler) so history
keeps accumulating even when `server.py` isn't running. Deliberately does its own scan via
`claude_db`'s lower-level `_scan_projects()`/`_scan_transcripts()` (the same pair `refresh()`
calls internally) rather than going through `refresh()`/`ledger.db` at all - `ledger.db` is a
disposable cache with no bearing on what `history.db` needs, and skipping it avoids the
serialized-row shape `fetch_transcripts()` returns (ISO strings/plain paths) not matching what
`upsert_history_transcripts()` expects (`datetime`/`Path` objects, straight from a fresh scan).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import claude_db


def backup() -> int:
    """Scan disk and upsert every transcript summary row into `history.db`.

    Returns the number of transcript rows scanned/upserted. Safe to call repeatedly - the
    upsert is keyed by `session_id`, so an unchanged session's row is overwritten with
    identical values rather than duplicated.
    """
    project_rows = claude_db._scan_projects()
    project_by_folder = {
        claude_db.sanitize_project_path(p["path"]): Path(p["path"]).name for p in project_rows
    }
    transcript_rows = claude_db._scan_transcripts(project_by_folder)
    claude_db.upsert_history_transcripts(transcript_rows)
    return len(transcript_rows)


def main(argv: Optional[Sequence[str]] = None) -> int:
    count = backup()
    print(f"Backed up {count} transcript row(s) to {claude_db.history_db_path()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
