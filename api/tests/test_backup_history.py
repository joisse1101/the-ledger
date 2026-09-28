"""backup_history.py - the standalone script that scans disk and upserts into history.db
without any server process running (mirrors the isolated_db fixture the rest of the
claude_db suite uses, so this never touches the real ~/.claude.json or ~/.claude/projects/)."""

import backup_history
import claude_db


def _write_one_session(tmp_path, write_config, write_transcript, session_id="s1"):
    write_config(tmp_path / "claude.json", {"/home/x/proj": {"hasTrustDialogAccepted": True}})
    folder = claude_db.sanitize_project_path("/home/x/proj")
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
    rows = claude_db.fetch_history_transcripts()
    assert [row["session_id"] for row in rows] == ["s1"]


def test_backup_does_not_require_ledger_db_to_exist(isolated_db, write_config, write_transcript):
    """No prior refresh()/server startup - the script's own scan is standalone."""
    tmp_path = isolated_db
    _write_one_session(tmp_path, write_config, write_transcript)
    assert not claude_db.db_path().exists()

    backup_history.backup()

    assert claude_db.fetch_history_transcripts()


def test_backup_run_twice_leaves_row_count_unchanged(isolated_db, write_config, write_transcript):
    tmp_path = isolated_db
    _write_one_session(tmp_path, write_config, write_transcript)

    backup_history.backup()
    first = claude_db.fetch_history_transcripts()

    backup_history.backup()
    second = claude_db.fetch_history_transcripts()

    assert len(first) == len(second) == 1
    assert [dict(r) for r in first] == [dict(r) for r in second]


def test_backup_updates_existing_session_in_place_on_a_later_run(
    isolated_db, write_config, write_transcript
):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {"/home/x/proj": {"hasTrustDialogAccepted": True}})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    path = tmp_path / "projects" / folder / "s1.jsonl"
    write_transcript(
        path,
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj", "sessionId": "s1"}],
    )
    backup_history.backup()
    assert claude_db.fetch_history_transcripts()[0]["message_count"] == 1

    write_transcript(
        path,
        [
            {"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj", "sessionId": "s1"},
            {"type": "user", "timestamp": "2024-01-01T10:01:00Z", "cwd": "/home/x/proj", "sessionId": "s1"},
        ],
    )
    backup_history.backup()

    rows = claude_db.fetch_history_transcripts()
    assert len(rows) == 1
    assert rows[0]["message_count"] == 2


def test_main_prints_row_count_and_returns_zero(isolated_db, write_config, write_transcript, capsys):
    tmp_path = isolated_db
    _write_one_session(tmp_path, write_config, write_transcript)

    exit_code = backup_history.main([])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Backed up 1 transcript row(s)" in out
