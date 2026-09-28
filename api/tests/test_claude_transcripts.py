from pathlib import Path

import claude_db
import claude_transcripts


def test_load_transcripts_maps_fields(isolated_db, write_config, write_transcript):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    write_transcript(
        tmp_path / "projects" / folder / "s1.jsonl",
        [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "cwd": "/home/x/proj",
                "version": "1.0.0",
                "gitBranch": "main",
                "sessionId": "s1",
                "message": {"content": "What's causing the login bug?"},
            },
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:05:00Z",
                "message": {
                    "id": "m1",
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 2, "cache_read_input_tokens": 300, "cache_creation_input_tokens": 40},
                },
            },
        ],
    )
    claude_db.refresh()

    transcripts = claude_transcripts.load_transcripts()
    assert len(transcripts) == 1
    t = transcripts[0]
    assert t.session_id == "s1"
    assert t.cwd == "/home/x/proj"
    assert t.version == "1.0.0"
    assert t.git_branch == "main"
    assert t.message_count == 2
    assert t.project == "proj"
    assert t.title == ""
    assert t.last_message == ""
    assert t.first_prompt == "What's causing the login bug?"
    assert t.context == 342


def test_delete_project_transcripts_removes_files_and_rows(
    isolated_db, write_config, write_transcript
):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    transcript_path = tmp_path / "projects" / folder / "s1.jsonl"
    write_transcript(
        transcript_path,
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj"}],
    )
    claude_db.refresh()

    removed_dirs = claude_transcripts.delete_project_transcripts("/home/x/proj")
    assert removed_dirs == 1
    assert not transcript_path.parent.exists()
    assert claude_transcripts.load_transcripts() == []


def test_delete_project_transcripts_no_match_is_a_noop(isolated_db, write_config):
    write_config(isolated_db / "claude.json", {})
    claude_db.refresh()
    assert claude_transcripts.delete_project_transcripts("/nonexistent") == 0


def test_delete_project_transcripts_ignores_drifted_cwd(
    isolated_db, write_config, write_transcript
):
    """A session that `cd`'d partway through leaves `cwd` pointing below the project root -
    deleting the project must still remove it, matched by its on-disk folder."""
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    transcript_path = tmp_path / "projects" / folder / "s1.jsonl"
    write_transcript(
        transcript_path,
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj/subdir"}],
    )
    claude_db.refresh()

    removed_dirs = claude_transcripts.delete_project_transcripts("/home/x/proj")
    assert removed_dirs == 1
    assert not transcript_path.parent.exists()
    assert claude_transcripts.load_transcripts() == []


def test_delete_transcript_removes_file_and_row(isolated_db, write_config, write_transcript):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    transcript_path = tmp_path / "projects" / folder / "s1.jsonl"
    write_transcript(
        transcript_path,
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "sessionId": "s1"}],
    )
    claude_db.refresh()

    assert claude_transcripts.delete_transcript("s1") is True
    assert not transcript_path.exists()
    assert claude_transcripts.load_transcripts() == []


def test_delete_transcript_returns_false_when_not_found(isolated_db, write_config):
    write_config(isolated_db / "claude.json", {})
    claude_db.refresh()
    assert claude_transcripts.delete_transcript("nonexistent") is False


def test_delete_transcript_purges_history_only_session(isolated_db, write_config, tmp_path):
    """A session already pruned from disk (known only from history.db) has no file left to
    unlink - the delete still succeeds and purges the history.db row."""
    write_config(isolated_db / "claude.json", {})
    claude_db.refresh()
    pruned_path = tmp_path / "gone" / "history-only.jsonl"  # never actually written to disk
    claude_db.upsert_history_transcripts(
        [
            {
                "session_id": "history-only",
                "path": pruned_path,
                "cwd": "/home/x/gone",
                "version": "1.0.0",
                "git_branch": "main",
                "started_at": None,
                "updated_at": None,
                "message_count": 1,
                "cost": 0.0,
                "context": None,
                "project": "gone",
                "title": "",
                "last_message": "",
                "first_prompt": "",
            }
        ]
    )

    assert claude_transcripts.delete_transcript("history-only") is True
    assert claude_transcripts.load_transcripts() == []
    assert claude_db.fetch_history_transcripts() == []


def test_delete_project_transcripts_purges_history_only_sessions(isolated_db, write_config):
    """A project whose only remaining record is in history.db (already pruned from disk and
    absent from ledger.db) still has its history.db rows removed by project delete."""
    write_config(isolated_db / "claude.json", {})
    claude_db.refresh()
    folder = claude_db.sanitize_project_path("/home/x/proj")
    claude_db.upsert_history_transcripts(
        [
            {
                "session_id": "history-only",
                "path": Path(f"/whatever/{folder}/history-only.jsonl"),
                "cwd": "/home/x/proj",
                "version": "1.0.0",
                "git_branch": "main",
                "started_at": None,
                "updated_at": None,
                "message_count": 1,
                "cost": 0.0,
                "context": None,
                "project": "proj",
                "title": "",
                "last_message": "",
                "first_prompt": "",
            }
        ]
    )

    removed_dirs = claude_transcripts.delete_project_transcripts("/home/x/proj")
    assert removed_dirs == 0  # nothing on disk to rmtree for a history-only session
    assert claude_db.fetch_history_transcripts() == []
