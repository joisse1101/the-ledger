from datetime import datetime
from pathlib import Path

import claude_db


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_sanitize_project_path_replaces_non_alnum():
    assert claude_db.sanitize_project_path("C:/Users/x/Repos/the-log") == (
        "C--Users-x-Repos-the-log"
    )


def test_sanitize_project_path_keeps_alnum():
    assert claude_db.sanitize_project_path("abc123") == "abc123"


def test_parse_epoch_ms_valid():
    dt = claude_db._parse_epoch_ms(1_700_000_000_000)
    assert dt == datetime.fromtimestamp(1_700_000_000_000 / 1000)


def test_parse_epoch_ms_rejects_non_numeric():
    assert claude_db._parse_epoch_ms("not-a-number") is None
    assert claude_db._parse_epoch_ms(None) is None


def test_parse_iso_timestamp_valid_with_z_suffix():
    dt = claude_db._parse_iso_timestamp("2024-01-15T10:30:00Z")
    assert dt is not None
    assert dt.year == 2024 and dt.month == 1 and dt.day == 15


def test_parse_iso_timestamp_rejects_invalid():
    assert claude_db._parse_iso_timestamp("not-a-timestamp") is None
    assert claude_db._parse_iso_timestamp(None) is None


def test_message_cost_unknown_model_returns_none():
    assert claude_db._message_cost("nonexistent-model", {"input_tokens": 100}) is None


def test_message_cost_basic_input_output():
    # sonnet-5: $2/1M input, $10/1M output
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    cost = claude_db._message_cost("claude-sonnet-5", usage)
    assert cost == 12.0


def test_message_cost_includes_cache_read_and_write():
    # opus-5: $5/1M input, $25/1M output
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 1_000_000,
        "cache_creation": {
            "ephemeral_5m_input_tokens": 1_000_000,
            "ephemeral_1h_input_tokens": 1_000_000,
        },
    }
    cost = claude_db._message_cost("claude-opus-5", usage)
    # 1M * 5 * 0.1 (read) + 1M * 5 * 1.25 (5m write) + 1M * 5 * 2.0 (1h write)
    expected = 5 * 0.1 + 5 * 1.25 + 5 * 2.0
    assert cost == expected


def test_message_cost_defaults_bare_cache_creation_to_5m_tier():
    usage = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 1_000_000}
    cost = claude_db._message_cost("claude-sonnet-5", usage)
    assert cost == 2 * 1.25


def test_extract_text_from_string_content():
    assert claude_db._extract_text("hello") == "hello"
    assert claude_db._extract_text("  ") is None


def test_extract_text_joins_text_blocks_and_ignores_others():
    content = [
        {"type": "text", "text": "part one"},
        {"type": "tool_use", "name": "Read"},
        {"type": "text", "text": "part two"},
    ]
    assert claude_db._extract_text(content) == "part one\n\npart two"


def test_extract_text_returns_none_for_no_text_blocks():
    assert claude_db._extract_text([{"type": "tool_use", "name": "Read"}]) is None
    assert claude_db._extract_text(None) is None


def test_clean_wrapper_tags_strips_command_and_system_reminder_tags():
    text = (
        "<system-reminder>context nobody typed</system-reminder>"
        "<command-name>/clear</command-name>"
    )
    assert claude_db._clean_wrapper_tags(text) is None


def test_clean_wrapper_tags_keeps_real_text_around_tags():
    text = "<system-reminder>context</system-reminder>What I actually asked"
    assert claude_db._clean_wrapper_tags(text) == "What I actually asked"


def test_normalize_snippet_collapses_whitespace():
    assert claude_db._normalize_snippet("a\n\n  b   c") == "a b c"


def test_normalize_snippet_truncates_long_text():
    result = claude_db._normalize_snippet("x" * 700, max_len=600)
    assert len(result) == 601  # 600 chars + ellipsis
    assert result.endswith("…")


# ---------------------------------------------------------------------------
# Transcript file scanning
# ---------------------------------------------------------------------------


def test_scan_transcript_file_aggregates_fields(tmp_path, write_transcript):
    path = tmp_path / "projects" / "somefolder" / "abc-123.jsonl"
    write_transcript(
        path,
        [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "cwd": "/home/x/repo",
                "version": "1.2.3",
                "gitBranch": "main",
                "sessionId": "abc-123",
            },
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:05:00Z",
                "message": {
                    "id": "msg_1",
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 1000, "output_tokens": 1000},
                },
            },
            # Duplicate line for the same assistant message id (multi-block
            # turn) - usage must only be counted once.
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:05:01Z",
                "message": {
                    "id": "msg_1",
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 1000, "output_tokens": 1000},
                },
            },
            {
                "type": "assistant",
                "isMeta": True,
                "timestamp": "2024-01-01T10:06:00Z",
            },
        ],
    )

    row = claude_db._scan_transcript_file(path, project_by_folder={})
    
    assert row is not None

    assert row["session_id"] == "abc-123"
    assert row["cwd"] == "/home/x/repo"
    assert row["version"] == "1.2.3"
    assert row["git_branch"] == "main"
    assert row["started_at"] == claude_db._parse_iso_timestamp("2024-01-01T10:00:00Z")
    assert row["updated_at"] == claude_db._parse_iso_timestamp("2024-01-01T10:06:00Z")
    # 1 user + 2 assistant lines are non-meta and counted individually (the
    # isMeta assistant line is excluded); message_count doesn't dedupe
    # repeated message ids the way cost does.
    assert row["message_count"] == 3
    # msg_1's usage counted once despite appearing on two lines.
    assert row["cost"] == claude_db._message_cost(
        "claude-sonnet-5", {"input_tokens": 1000, "output_tokens": 1000}
    )
    # No project_by_folder match -> falls back to cwd's last path component.
    assert row["project"] == "repo"


def test_scan_transcript_file_project_prefers_folder_match(tmp_path, write_transcript):
    path = tmp_path / "projects" / "sanitized-folder" / "abc-123.jsonl"
    write_transcript(
        path,
        [{"type": "user", "cwd": "/some/other/nested/dir", "timestamp": "2024-01-01T10:00:00Z"}],
    )

    row = claude_db._scan_transcript_file(
        path, project_by_folder={"sanitized-folder": "real-project-name"}
    )
    assert row is not None
    assert row["project"] == "real-project-name"


def test_scan_transcript_file_no_cwd_falls_back_to_parent_folder_name(
    tmp_path, write_transcript
):
    path = tmp_path / "projects" / "some-folder" / "abc-123.jsonl"
    write_transcript(path, [{"type": "user", "timestamp": "2024-01-01T10:00:00Z"}])

    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row is not None
    assert row["project"] == "some-folder"


def test_scan_transcript_file_recap_prefers_ai_title(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {"type": "user", "timestamp": "2024-01-01T10:00:00Z", "message": {"content": "hi"}},
            {"type": "ai-title", "aiTitle": "Fix login bug"},
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:05:00Z",
                "message": {"content": [{"type": "text", "text": "Done, fixed it."}]},
            },
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["recap"] == "Fix login bug"
    assert row["recap_source"] == "title"


def test_scan_transcript_file_recap_falls_back_to_last_assistant_text(
    tmp_path, write_transcript
):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {"type": "user", "timestamp": "2024-01-01T10:00:00Z", "message": {"content": "hi"}},
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:01:00Z",
                "message": {"content": [{"type": "text", "text": "First reply."}]},
            },
            # A tool-only turn (no text block) must not blank out the recap.
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:02:00Z",
                "message": {"content": [{"type": "tool_use", "name": "Read"}]},
            },
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:03:00Z",
                "message": {"content": [{"type": "text", "text": "Anything else?"}]},
            },
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["recap"] == "Anything else?"
    assert row["recap_source"] == "last_message"


def test_scan_transcript_file_recap_falls_back_to_first_user_prompt(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "message": {"content": "Help me fix the login bug"},
            }
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["recap"] == "Help me fix the login bug"
    assert row["recap_source"] == "first_prompt"


def test_scan_transcript_file_recap_skips_command_only_first_message(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "message": {"content": "<command-name>/clear</command-name>"},
            },
            {
                "type": "user",
                "timestamp": "2024-01-01T10:01:00Z",
                "message": {"content": "Now the real question"},
            },
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["recap"] == "Now the real question"
    assert row["recap_source"] == "first_prompt"


def test_scan_transcript_file_recap_blank_when_no_content(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(path, [{"type": "system", "timestamp": "2024-01-01T10:00:00Z"}])
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["recap"] == ""
    assert row["recap_source"] == ""


def test_scan_transcript_file_skips_malformed_lines(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(
        "not json\n" + '{"type": "user", "timestamp": "2024-01-01T10:00:00Z"}\n',
        encoding="utf-8",
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row is not None
    assert row["message_count"] == 1


# ---------------------------------------------------------------------------
# refresh() / fetch / delete round trip
# ---------------------------------------------------------------------------


def test_refreshed_at_is_none_before_first_refresh(isolated_db):
    assert claude_db.refreshed_at() is None


def test_refresh_populates_projects_and_transcripts(isolated_db, write_config, write_transcript):
    tmp_path = isolated_db
    write_config(
        tmp_path / "claude.json",
        {
            "/home/x/the-ledger": {
                "hasTrustDialogAccepted": True,
                "lastSessionId": "sess-1",
                "lastVersionBase": "1.0.0",
                "lastCost": 1.5,
                "lastStartTime": 1_700_000_000_000,
                "lastDuration": 60000,
                "lastLinesAdded": 10,
                "lastLinesRemoved": 2,
                "mcpServers": {"b-server": {}, "a-server": {}},
            }
        },
    )
    folder = claude_db.sanitize_project_path("/home/x/the-ledger")
    write_transcript(
        tmp_path / "projects" / folder / "sess-1.jsonl",
        [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "cwd": "/home/x/the-ledger",
                "sessionId": "sess-1",
            }
        ],
    )

    refreshed = claude_db.refresh()
    assert isinstance(refreshed, datetime)
    assert claude_db.refreshed_at() == refreshed

    projects = claude_db.fetch_projects()
    assert len(projects) == 1
    assert projects[0]["path"] == "/home/x/the-ledger"
    assert projects[0]["trust_accepted"] == 1
    assert projects[0]["mcp_servers"] == '["a-server", "b-server"]'

    transcripts = claude_db.fetch_transcripts()
    assert len(transcripts) == 1
    assert transcripts[0]["session_id"] == "sess-1"
    assert transcripts[0]["project"] == "the-ledger"


def test_refresh_replaces_previous_contents(isolated_db, write_config):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {"/a": {"hasTrustDialogAccepted": False}})
    claude_db.refresh()
    assert len(claude_db.fetch_projects()) == 1

    write_config(tmp_path / "claude.json", {"/b": {"hasTrustDialogAccepted": False}})
    claude_db.refresh()
    projects = claude_db.fetch_projects()
    assert len(projects) == 1
    assert projects[0]["path"] == "/b"


def test_delete_project_row(isolated_db, write_config):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {"/a": {}, "/b": {}})
    claude_db.refresh()
    assert len(claude_db.fetch_projects()) == 2

    claude_db.delete_project_row("/a")
    remaining = claude_db.fetch_projects()
    assert len(remaining) == 1
    assert remaining[0]["path"] == "/b"


def test_transcript_lookup_and_delete_by_cwd(isolated_db, write_config, write_transcript):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    write_transcript(
        tmp_path / "projects" / folder / "s1.jsonl",
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj"}],
    )
    claude_db.refresh()

    paths = claude_db.transcript_paths_for_cwd("/home/x/proj")
    assert len(paths) == 1
    assert paths[0] == tmp_path / "projects" / folder / "s1.jsonl"

    claude_db.delete_transcript_rows_by_cwd("/home/x/proj")
    assert claude_db.fetch_transcripts() == []


def test_transcript_lookup_and_delete_by_session_id(isolated_db, write_config, write_transcript):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    write_transcript(
        tmp_path / "projects" / folder / "s1.jsonl",
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "sessionId": "s1"}],
    )
    claude_db.refresh()

    assert claude_db.transcript_path_for_session("s1") == (
        tmp_path / "projects" / folder / "s1.jsonl"
    )
    assert claude_db.transcript_path_for_session("nonexistent") is None

    claude_db.delete_transcript_row("s1")
    assert claude_db.fetch_transcripts() == []
