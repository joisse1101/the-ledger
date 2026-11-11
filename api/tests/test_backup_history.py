"""backup_history.py - the standalone script that scans disk and upserts into history.db
without any server process running (mirrors the isolated_db fixture the rest of the
db suite uses, so this never touches the real ~/.claude.json or ~/.claude/projects/)."""

import backup_history
import pytest
from app.repositories import settings_store
from app.repositories.db import history, paths


def _write_one_session(tmp_path, write_config, write_transcript, session_id="s1"):
    write_config(tmp_path / "claude.json", {"/home/x/proj": {"hasTrustDialogAccepted": True}})
    folder = paths.sanitize_project_path("/home/x/proj")
    write_transcript(
        tmp_path / "projects" / folder / f"{session_id}.jsonl",
        [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "cwd": "/home/x/proj",
                "sessionId": session_id,
            }
        ],
    )


def test_backup_scans_disk_and_upserts_into_history_db(isolated_db, write_config, write_transcript):
    tmp_path = isolated_db
    _write_one_session(tmp_path, write_config, write_transcript)

    count = backup_history.backup()

    assert count == 1
    rows = history.fetch_history_transcripts()
    assert [row["session_id"] for row in rows] == ["s1"]


def test_backup_does_not_require_ledger_db_to_exist(isolated_db, write_config, write_transcript):
    """No prior refresh()/server startup - the script's own scan is standalone."""
    tmp_path = isolated_db
    _write_one_session(tmp_path, write_config, write_transcript)
    assert not paths.db_path().exists()

    backup_history.backup()

    assert history.fetch_history_transcripts()


def test_backup_run_twice_leaves_row_count_unchanged(isolated_db, write_config, write_transcript):
    tmp_path = isolated_db
    _write_one_session(tmp_path, write_config, write_transcript)

    backup_history.backup()
    first = history.fetch_history_transcripts()

    backup_history.backup()
    second = history.fetch_history_transcripts()

    assert len(first) == len(second) == 1
    assert [dict(r) for r in first] == [dict(r) for r in second]


def test_backup_updates_existing_session_in_place_on_a_later_run(
    isolated_db, write_config, write_transcript
):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {"/home/x/proj": {"hasTrustDialogAccepted": True}})
    folder = paths.sanitize_project_path("/home/x/proj")
    path = tmp_path / "projects" / folder / "s1.jsonl"
    write_transcript(
        path,
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj", "sessionId": "s1"}],
    )
    backup_history.backup()
    assert history.fetch_history_transcripts()[0]["message_count"] == 1

    write_transcript(
        path,
        [
            {"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj", "sessionId": "s1"},
            {"type": "user", "timestamp": "2024-01-01T10:01:00Z", "cwd": "/home/x/proj", "sessionId": "s1"},
        ],
    )
    backup_history.backup()

    rows = history.fetch_history_transcripts()
    assert len(rows) == 1
    assert rows[0]["message_count"] == 2


def test_main_prints_row_count_and_returns_zero(isolated_db, write_config, write_transcript, capsys):
    tmp_path = isolated_db
    _write_one_session(tmp_path, write_config, write_transcript)

    exit_code = backup_history.main([])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Backed up 1 transcript row(s)" in out


def test_backup_attributes_a_session_in_a_configured_worktree_folder(
    isolated_db, write_config, write_transcript
):
    settings_store.save_worktree_folders([".trees"])
    write_config(isolated_db / "claude.json", {})
    worktree = "/home/x/the-ledger/.trees/fix-nav"
    write_transcript(
        isolated_db / "projects" / paths.sanitize_project_path(worktree) / "s1.jsonl",
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": worktree, "sessionId": "s1"}],
    )

    backup_history.backup()

    (row,) = history.fetch_history_transcripts()
    assert (row["worktree"], row["project"]) == ("fix-nav", "the-ledger")


def test_main_logs_a_start_line_and_a_success_line_beside_history_db(
    isolated_db, write_config, write_transcript
):
    _write_one_session(isolated_db, write_config, write_transcript)

    backup_history.main([])

    lines = backup_history.log_path().read_text(encoding="utf-8").splitlines()
    assert backup_history.log_path().parent == paths.history_db_path().parent
    assert len(lines) == 2
    assert lines[0].endswith("Ledger: Backing up history...")
    assert lines[1].endswith("Ledger: Backup succeeded: 1 transcript row(s)")


def test_main_logs_a_start_line_and_a_failure_line_then_still_fails(isolated_db, monkeypatch):
    def broken_scan():
        raise RuntimeError("disk unreadable")

    monkeypatch.setattr(backup_history.scanner, "scan_projects", broken_scan)

    with pytest.raises(RuntimeError, match="disk unreadable"):
        backup_history.main([])

    lines = backup_history.log_path().read_text(encoding="utf-8").splitlines()
    assert lines[0].endswith("Ledger: Backing up history...")
    assert lines[1].endswith("Ledger: Backup failed: RuntimeError: disk unreadable")


def test_a_log_that_cannot_be_written_does_not_fail_the_backup(
    isolated_db, write_config, write_transcript, monkeypatch
):
    _write_one_session(isolated_db, write_config, write_transcript)
    log_path = backup_history.log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.mkdir()  # a folder where the log file should be, so opening it for append fails

    assert backup_history.main([]) == 0
    assert len(history.fetch_history_transcripts()) == 1
