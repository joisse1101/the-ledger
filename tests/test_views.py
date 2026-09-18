from datetime import datetime
from pathlib import Path

from claude_projects import ClaudeProject
from claude_sessions import ClaudeSession
from claude_transcripts import ClaudeTranscript
from views.projects import _projects_dataframe
from views.sessions import _sessions_dataframe, _transcripts_dataframe


def _session(**overrides):
    defaults = dict(
        pid=1,
        session_id="s1",
        cwd="/x/proj",
        name="my-session",
        status="running",
        kind="cli",
        entrypoint="cli",
        version="1.0",
        started_at=datetime(2024, 1, 1, 9, 0, 0),
        updated_at=datetime(2024, 1, 1, 9, 5, 0),
        status_updated_at=datetime(2024, 1, 1, 9, 5, 0),
        raw={},
        project="proj",
    )
    defaults.update(overrides)
    return ClaudeSession(**defaults)


def _transcript(**overrides):
    defaults = dict(
        session_id="t1",
        path=Path("t1.jsonl"),
        cwd="/x/proj",
        version="1.0",
        git_branch="main",
        started_at=datetime(2024, 1, 1, 9, 0, 0),
        updated_at=datetime(2024, 1, 1, 9, 5, 0),
        message_count=4,
        cost=0.5,
        project="proj",
        recap="Fixed the login bug",
        recap_source="title",
    )
    defaults.update(overrides)
    return ClaudeTranscript(**defaults)


def _project(**overrides):
    defaults = dict(
        path="/x/proj",
        trust_accepted=True,
        last_session_id="s1",
        last_version="1.0",
        last_cost=1.0,
        last_start_time=datetime(2024, 1, 1, 9, 0, 0),
        last_duration_ms=1000,
        lines_added=5,
        lines_removed=2,
        mcp_servers=["a", "b"],
    )
    defaults.update(overrides)
    return ClaudeProject(**defaults)


def test_sessions_dataframe_maps_fields(monkeypatch):
    import views.sessions as sessions_view

    monkeypatch.setattr(sessions_view, "load_sessions", lambda: [_session()])
    df = _sessions_dataframe()
    assert list(df.iloc[0][["Name", "Project", "Status", "PID", "Session ID"]]) == [
        "my-session",
        "proj",
        "running",
        1,
        "s1",
    ]


def test_sessions_dataframe_empty(monkeypatch):
    import views.sessions as sessions_view

    monkeypatch.setattr(sessions_view, "load_sessions", lambda: [])
    df = _sessions_dataframe()
    assert df.empty


def test_transcripts_dataframe_maps_fields(monkeypatch):
    import views.sessions as sessions_view

    monkeypatch.setattr(sessions_view, "load_transcripts", lambda: [_transcript()])
    df = _transcripts_dataframe()
    row = df.iloc[0]
    assert row["Session ID"] == "t1"
    assert row["Messages"] == 4
    assert row["Est. Cost ($)"] == 0.5
    assert row["Git Branch"] == "main"


def test_projects_dataframe_maps_fields(monkeypatch):
    import views.projects as projects_view

    monkeypatch.setattr(projects_view, "load_projects", lambda: [_project()])
    df = _projects_dataframe()
    row = df.iloc[0]
    assert row["Name"] == "proj"
    assert row["Trusted"] == True  # noqa: E712 - pandas bool cell, not a Python bool
    assert row["Lines +/-"] == "+5/-2"
    assert row["MCP Servers"] == "a, b"


def test_projects_dataframe_handles_missing_lines_and_servers(monkeypatch):
    import views.projects as projects_view

    monkeypatch.setattr(
        projects_view,
        "load_projects",
        lambda: [_project(lines_added=None, lines_removed=None, mcp_servers=[])],
    )
    df = _projects_dataframe()
    row = df.iloc[0]
    assert row["Lines +/-"] is None
    assert row["MCP Servers"] is None


def test_projects_dataframe_empty(monkeypatch):
    import views.projects as projects_view

    monkeypatch.setattr(projects_view, "load_projects", lambda: [])
    df = _projects_dataframe()
    assert df.empty
