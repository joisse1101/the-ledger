"""Standalone daily backup: scans Claude Code's on-disk data and upserts it into
`history.db`, Ledger's durable transcript store - see `openspec/changes/add-transcript-history-backup/`.

Meant to be triggered by an OS-level scheduled task (e.g. Windows Task Scheduler) so history
keeps accumulating even when the backend isn't running. Deliberately does its own scan via
the scanner's `scan_projects()`/`scan_transcripts()` (the same pair `refresh()`
calls internally) rather than going through `refresh()`/`ledger.db` at all - `ledger.db` is a
disposable cache with no bearing on what `history.db` needs, and skipping it avoids the
serialized-row shape `fetch_transcripts()` returns (ISO strings/plain paths) not matching what
`upsert_history_transcripts()` expects (`datetime`/`Path` objects, straight from a fresh scan).
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from app.repositories.db import history, paths, scanner

logger = logging.getLogger(__name__)

START_MESSAGE = "Ledger: Backing up history..."
LOG_FILE_NAME = "backup.log"


def log_path() -> Path:
    """The log file sits beside history.db, so it is found wherever the data folder is."""
    return paths.history_db_path().with_name(LOG_FILE_NAME)


def _log(message: str) -> None:
    """Append one timestamped line. The scheduled task runs without a console, so this file is the
    only record of a run. A logging problem must never fail the backup, so it is only reported."""
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{datetime.now().astimezone().isoformat(timespec='seconds')} {message}\n")
    except OSError:
        logger.warning("could not write the backup log", exc_info=True)


def backup() -> int:
    """Scan disk and upsert every transcript summary row into `history.db`.

    Returns the number of transcript rows scanned/upserted. Safe to call repeatedly - the
    upsert is keyed by `session_id`, so an unchanged session's row is overwritten with
    identical values rather than duplicated.
    """
    project_rows = scanner.scan_projects()
    project_by_folder = {
        paths.sanitize_project_path(p["path"]): Path(p["path"]).name for p in project_rows
    }
    transcript_rows = scanner.scan_transcripts(project_by_folder)
    history.upsert_history_transcripts(transcript_rows)
    return len(transcript_rows)


def main(argv: Optional[Sequence[str]] = None) -> int:
    _log(START_MESSAGE)
    try:
        count = backup()
    except Exception as error:
        _log(f"Ledger: Backup failed: {type(error).__name__}: {error}")
        raise
    _log(f"Ledger: Backup succeeded: {count} transcript row(s)")
    print(f"Backed up {count} transcript row(s) to {paths.history_db_path()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
