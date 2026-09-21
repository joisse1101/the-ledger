from datetime import datetime
from pathlib import Path

import pytest

from claude_context import LiveContext
from claude_projects import ClaudeProject
from claude_sessions import ClaudeSession
from claude_transcripts import ClaudeTranscript
from views.projects import _projects_dataframe
from views.sessions_data import _sessions_dataframe, _sort_transcripts_dataframe, _transcripts_dataframe


@pytest.fixture(autouse=True)
def _no_real_transcripts(monkeypatch):
    """Keep the Live table's Context lookup off the real ~/.claude/projects/ unless a test stubs it."""
    import views.sessions_data as sessions_view

    monkeypatch.setattr(sessions_view, "live_context", lambda session_id, cwd: None)


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
    return ClaudeSession(**defaults) # type: ignore


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
        title="Fixed the login bug",
        last_message="All done, let me know if you need anything else.",
        first_prompt="Can you fix the login bug?",
        context=120_000,
    )
    defaults.update(overrides)
    return ClaudeTranscript(**defaults) # type: ignore


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
    return ClaudeProject(**defaults) # type: ignore


def test_sessions_dataframe_maps_fields(monkeypatch):
    import views.sessions_data as sessions_view

    monkeypatch.setattr(sessions_view, "load_sessions", lambda: [_session()])
    df = _sessions_dataframe()
    assert list(df.iloc[0][["Name", "Project", "Status", "PID", "Session ID"]]) == [
        "my-session",
        "proj",
        "running",
        1,
        "s1",
    ]


def test_sessions_dataframe_context_cell_is_formatted(monkeypatch):
    import views.sessions_data as sessions_view

    calls = []

    def fake_live_context(session_id, cwd):
        calls.append((session_id, cwd))
        return LiveContext(size=394_000, growth=2_100, history=[390_000, 394_000])

    monkeypatch.setattr(sessions_view, "load_sessions", lambda: [_session()])
    monkeypatch.setattr(sessions_view, "live_context", fake_live_context)
    cell = _sessions_dataframe().iloc[0]["Context"]
    assert cell.startswith("394k ▲ +2.1k ")
    assert calls == [("s1", "/x/proj")]


def test_sessions_dataframe_context_cell_is_a_placeholder_when_unavailable(monkeypatch):
    import views.sessions_data as sessions_view

    monkeypatch.setattr(sessions_view, "load_sessions", lambda: [_session()])
    assert _sessions_dataframe().iloc[0]["Context"] == "--"


def test_sessions_dataframe_one_failing_context_read_leaves_other_rows_populated(monkeypatch):
    import views.sessions_data as sessions_view

    def fake_live_context(session_id, cwd):
        if session_id == "bad":
            raise RuntimeError("unreadable")
        return LiveContext(size=42_000, growth=None, history=[42_000])

    monkeypatch.setattr(sessions_view, "load_sessions", lambda: [_session(session_id="bad", pid=1), _session(session_id="good", pid=2)])
    monkeypatch.setattr(sessions_view, "live_context", fake_live_context)
    df = _sessions_dataframe()
    assert list(df["Context"]) == ["--", "42k"]
    assert list(df["Session ID"]) == ["bad", "good"]


def test_sessions_dataframe_empty(monkeypatch):
    import views.sessions_data as sessions_view

    monkeypatch.setattr(sessions_view, "load_sessions", lambda: [])
    df = _sessions_dataframe()
    assert df.empty


def test_transcripts_dataframe_maps_fields(monkeypatch):
    import views.sessions_data as sessions_view

    monkeypatch.setattr(sessions_view, "load_transcripts", lambda: [_transcript()])
    df = _transcripts_dataframe()
    row = df.iloc[0]
    assert row["Session ID"] == "t1"
    assert row["Title"] == "Fixed the login bug"
    assert row["Messages"] == 4
    assert row["Cost ($)"] == 0.5
    assert row["Git Branch"] == "main"
    assert row["Context"] == 120_000
    assert (
        row["CWD"] == "/x/proj"
    )  # the detail dialog needs it to locate the transcript


def test_transcripts_dataframe_context_is_numeric_so_it_sorts_and_formats_missing_as_placeholder(monkeypatch):
    import views.sessions_data as sessions_view
    from views.sessions_table import _format_context

    monkeypatch.setattr(sessions_view, "load_transcripts", lambda: [
        _transcript(session_id="a", context=9_000), _transcript(session_id="b", context=None), _transcript(session_id="c", context=120_000)])
    df = _sort_transcripts_dataframe(_transcripts_dataframe(), "Context", ascending=False)
    assert list(df["Session ID"]) == ["c", "a", "b"]
    assert [_format_context(v) for v in df["Context"]] == ["120k", "9k", "--"]


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


# ---------------------------------------------------------------- Live row context detail


def _detail(*entries):
    import json

    from claude_context import parse_detail

    return parse_detail(json.dumps(entry) for entry in entries)


def _assistant_line(message_id, *, read=0, written=0, tools=()):
    return {
        "type": "assistant",
        "timestamp": "2026-09-18T04:12:10.124Z",
        "message": {
            "id": message_id,
            "model": "claude-sonnet-5",
            "content": [{"type": "tool_use", "name": name, "input": tool_input} for name, tool_input in tools],
            "usage": {"input_tokens": 0, "cache_read_input_tokens": read, "cache_creation_input_tokens": written,
                      "output_tokens": 7},
        },
    }


def test_context_detail_history_dataframe_marks_cache_misses_and_compactions():
    from views.sessions_context import _history_dataframe

    boundary = {"type": "system", "subtype": "compact_boundary", "compactMetadata": {"trigger": "auto", "preTokens": 9}}
    detail = _detail(
        _assistant_line("m1", read=100, written=900),
        _assistant_line("m2", read=50, written=400),
        boundary,
        _assistant_line("m3", read=10),
    )
    df = _history_dataframe(detail)
    assert list(df["#"]) == [1, 2, 3]
    assert list(df["Cache read"]) == [100, 50, 10]
    assert list(df["Output"]) == [7, 7, 7]
    assert list(df["Note"]) == ["", "cache miss", "compacted before this response"]


def test_context_detail_marker_records_and_captions():
    from views.sessions_context import _cache_miss_records, _chart_records, _compaction_captions, _compaction_records

    boundary = {"type": "system", "subtype": "compact_boundary", "compactMetadata": {"trigger": "manual", "preTokens": 191_736}}
    detail = _detail(_assistant_line("m1", read=100, written=900), _assistant_line("m2", read=5, written=40), boundary)
    assert [r["Response"] for r in _cache_miss_records(detail)] == [2]
    assert _compaction_records(detail) == [{"Response": 3, "Note": "Compaction"}]
    assert _compaction_captions(detail) == ["Compacted (manual) after response 2, was 192k"]
    assert [(r["Response"], r["Kind"], r["Tokens"]) for r in _chart_records(detail) if r["Response"] == 1] == [
        (1, "Cache read", 100), (1, "Cache written", 900), (1, "New", 0)]


def test_context_detail_attribution_dataframes():
    from views.sessions_context import _by_tool_dataframe, _largest_dataframe

    detail = _detail(
        _assistant_line("m1", read=1_000, tools=[("Read", {"file_path": "a.py"})]),
        _assistant_line("m2", read=5_000, tools=[("Bash", {"command": "ls"})]),
        _assistant_line("m3", read=6_000),
    )
    assert _by_tool_dataframe(detail).to_dict("records") == [
        {"Tool": "Read", "Tokens": 4_000, "Uses": 1}, {"Tool": "Bash", "Tokens": 1_000, "Uses": 1}]
    assert _largest_dataframe(detail).to_dict("records") == [
        {"Response": 2, "Tokens": 4_000, "Tool": "Read", "Hint": "a.py"},
        {"Response": 3, "Tokens": 1_000, "Tool": "Bash", "Hint": "ls"}]
    assert _by_tool_dataframe(_detail()).empty
