import json

import claude_sessions


def _write_session_file(path, **overrides):
    data = {
        "pid": 1234,
        "sessionId": "sess-1",
        "cwd": "/home/x/proj",
        "name": "my-session",
        "status": "running",
        "kind": "cli",
        "entrypoint": "cli",
        "version": "1.0.0",
        "startedAt": 1_700_000_000_000,
        "updatedAt": 1_700_000_100_000,
        "statusUpdatedAt": 1_700_000_100_000,
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_parse_session_file_valid(tmp_path):
    path = tmp_path / "1234.json"
    _write_session_file(path)
    session = claude_sessions._parse_session_file(path)
    assert session is not None
    assert session.pid == 1234
    assert session.session_id == "sess-1"
    assert session.project == "proj"  # derived from cwd before transcript lookup


def test_parse_session_file_missing_required_fields(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"cwd": "/x"}), encoding="utf-8")
    assert claude_sessions._parse_session_file(path) is None


def test_parse_session_file_malformed_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")
    assert claude_sessions._parse_session_file(path) is None


def test_load_sessions_empty_directory_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_sessions, "load_transcripts", lambda: [])
    assert claude_sessions.load_sessions(tmp_path / "does-not-exist") == []


def test_load_sessions_sorted_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_sessions, "load_transcripts", lambda: [])
    _write_session_file(tmp_path / "1.json", sessionId="older", updatedAt=1_700_000_000_000)
    _write_session_file(tmp_path / "2.json", sessionId="newer", updatedAt=1_700_000_500_000)

    sessions = claude_sessions.load_sessions(tmp_path)
    assert [s.session_id for s in sessions] == ["newer", "older"]


def test_load_sessions_resolves_project_from_transcripts(tmp_path, monkeypatch):
    class FakeTranscript:
        def __init__(self, session_id, project):
            self.session_id = session_id
            self.project = project
            self.recap = "What we did"
            self.recap_source = "title"

    monkeypatch.setattr(
        claude_sessions,
        "load_transcripts",
        lambda: [FakeTranscript("sess-1", "real-project-name")],
    )
    _write_session_file(tmp_path / "1.json", sessionId="sess-1", cwd="/some/other/path")

    sessions = claude_sessions.load_sessions(tmp_path)
    assert sessions[0].project == "real-project-name"
    assert sessions[0].recap == "What we did"
    assert sessions[0].recap_source == "title"


def test_load_sessions_no_transcript_match_leaves_recap_blank(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_sessions, "load_transcripts", lambda: [])
    _write_session_file(tmp_path / "1.json", sessionId="sess-1")

    sessions = claude_sessions.load_sessions(tmp_path)
    assert sessions[0].recap == ""
    assert sessions[0].recap_source == ""


def test_load_sessions_falls_back_to_cwd_when_no_transcript_match(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_sessions, "load_transcripts", lambda: [])
    _write_session_file(tmp_path / "1.json", sessionId="sess-1", cwd="/home/x/brand-new")

    sessions = claude_sessions.load_sessions(tmp_path)
    assert sessions[0].project == "brand-new"


def test_load_sessions_caches_unchanged_files(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_sessions, "load_transcripts", lambda: [])
    path = tmp_path / "1.json"
    _write_session_file(path, sessionId="sess-1")

    first = claude_sessions.load_sessions(tmp_path)
    second = claude_sessions.load_sessions(tmp_path)
    assert first[0] is second[0]


def test_load_sessions_reparses_changed_files(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_sessions, "load_transcripts", lambda: [])
    path = tmp_path / "1.json"
    _write_session_file(path, sessionId="sess-1", status="running")

    first = claude_sessions.load_sessions(tmp_path)
    assert first[0].status == "running"

    # Force a distinct mtime (some filesystems have coarse mtime resolution).
    import os
    import time

    _write_session_file(path, sessionId="sess-1", status="stopped")
    os.utime(path, (time.time() + 5, time.time() + 5))

    second = claude_sessions.load_sessions(tmp_path)
    assert second[0].status == "stopped"


def test_load_sessions_drops_stale_cache_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_sessions, "load_transcripts", lambda: [])
    path = tmp_path / "1.json"
    _write_session_file(path, sessionId="sess-1")
    claude_sessions.load_sessions(tmp_path)
    assert path in claude_sessions._cache

    path.unlink()
    claude_sessions.load_sessions(tmp_path)
    assert path not in claude_sessions._cache
