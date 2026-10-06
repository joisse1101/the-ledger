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


def test_normalize_snippet_removes_headers_and_prose_emphasis():
    snippet = claude_db._normalize_snippet("# *A **very** useful* heading #\n\nText")
    assert snippet == "A very useful heading Text"


def test_normalize_snippet_preserves_inline_code_symbols_and_emoji():
    snippet = claude_db._normalize_snippet(
        "Use `value = left ** right` with **bold** *italic* _words_ \N{ROCKET}"
    )
    assert snippet == "Use `value = left ** right` with bold italic words \N{ROCKET}"


def test_normalize_snippet_preserves_multi_backtick_inline_code():
    snippet = claude_db._normalize_snippet("Use ``a ` symbol`` and **not this**")
    assert snippet == "Use ``a ` symbol`` and not this"


def test_normalize_snippet_preserves_fenced_code_formatting():
    snippet = claude_db._normalize_snippet(
        "## Example\n\n```python\n# Keep **this** exactly\nprint('\N{ROCKET}')\n```\n\n*Done*"
    )
    assert snippet == "Example\n\n```python\n# Keep **this** exactly\nprint('\N{ROCKET}')\n```\n\nDone"


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


def _cost_state(total, *, has_unknown=False):
    return {"type": "cost-state", "totalCostUSD": total, "hasUnknownModelCost": has_unknown}


def test_scan_transcript_file_prefers_clean_cost_state_line(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:05:00Z",
                "message": {
                    "id": "m1",
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
                },
            },
            _cost_state(3.34),
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    # cost-state's own total wins over the per-message sum (which would be $12.0 here).
    assert row["cost"] == 3.34
    assert row["cost_source"] == "exact"
    assert row["cost_state_flagged"] is False


def test_scan_transcript_file_last_cost_state_line_wins(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(path, [_cost_state(1.0), _cost_state(2.0), _cost_state(3.0)])
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["cost"] == 3.0
    assert row["cost_source"] == "exact"


def test_scan_transcript_file_cost_state_with_unknown_model_falls_back_to_estimate(
    tmp_path, write_transcript
):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:05:00Z",
                "message": {
                    "id": "m1",
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
                },
            },
            _cost_state(3.34, has_unknown=True),
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    # Falls back to the per-message sum, not the flagged cost-state total.
    assert row["cost"] == claude_db._message_cost(
        "claude-sonnet-5", {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    )
    assert row["cost_source"] == "estimated"
    assert row["cost_state_flagged"] is True


def test_scan_transcript_file_no_cost_state_line_is_estimated_and_unflagged(
    tmp_path, write_transcript
):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:05:00Z",
                "message": {
                    "id": "m1",
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 1000, "output_tokens": 1000},
                },
            },
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["cost_source"] == "estimated"
    assert row["cost_state_flagged"] is False


def _assistant_turn(message_id, model, *, sidechain=False):
    return {
        "type": "assistant",
        "isSidechain": sidechain,
        "timestamp": "2024-01-01T10:05:00Z",
        "message": {"id": message_id, "model": model, "usage": {"input_tokens": 1, "output_tokens": 1}},
    }


def test_scan_transcript_file_model_is_the_most_used_main_thread_model(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            _assistant_turn("m1", "model-a"),
            _assistant_turn("m2", "model-b"),
            _assistant_turn("m3", "model-b"),
            _assistant_turn("m3", "model-b"),  # repeated line of the same response: counted once
            _assistant_turn("m4", "model-a", sidechain=True),
            _assistant_turn("m5", "model-a", sidechain=True),
            _assistant_turn("m6", "<synthetic>"),
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["model"] == "model-b"


def test_scan_transcript_file_model_is_blank_without_assistant_turns(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(path, [_cost_state(1.0)])
    assert claude_db._scan_transcript_file(path, project_by_folder={})["model"] == ""


def test_scan_transcript_file_unpriced_models_collects_unrecognized_model_ids(
    tmp_path, write_transcript
):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:05:00Z",
                "message": {
                    "id": "m1",
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 1000, "output_tokens": 1000},
                },
            },
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:06:00Z",
                "message": {
                    "id": "m2",
                    "model": "claude-fake-model-b",
                    "usage": {"input_tokens": 1000, "output_tokens": 1000},
                },
            },
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:07:00Z",
                "message": {
                    "id": "m3",
                    "model": "claude-fake-model-a",
                    "usage": {"input_tokens": 1000, "output_tokens": 1000},
                },
            },
            # Repeat an already-seen unrecognized model - de-duplicated, not repeated.
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:08:00Z",
                "message": {
                    "id": "m4",
                    "model": "claude-fake-model-b",
                    "usage": {"input_tokens": 1000, "output_tokens": 1000},
                },
            },
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["unpriced_models"] == ["claude-fake-model-a", "claude-fake-model-b"]


def test_scan_transcript_file_unpriced_models_empty_when_all_recognized(
    tmp_path, write_transcript
):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:05:00Z",
                "message": {
                    "id": "m1",
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 1000, "output_tokens": 1000},
                },
            },
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["unpriced_models"] == []


def _assistant(message_id, *, new=0, read=0, written=0, model="claude-sonnet-5", **extra):
    return {
        "type": "assistant",
        "timestamp": "2024-01-01T10:05:00Z",
        "message": {
            "id": message_id,
            "model": model,
            "usage": {
                "input_tokens": new,
                "cache_read_input_tokens": read,
                "cache_creation_input_tokens": written,
                "output_tokens": 5,
            },
        },
        **extra,
    }


def test_scan_transcript_file_context_is_the_last_real_turns_total(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            _assistant("m1", new=10, read=100, written=1_000),
            _assistant("m2", new=5, read=2_000, written=300),
            # Repeated line of the same multi-block turn: last line's usage wins.
            _assistant("m2", new=5, read=2_000, written=300),
            # None of these is a real main-thread response, so none may become the context.
            _assistant("side", new=99_999, isSidechain=True),
            _assistant("synth", new=99_999, model="<synthetic>"),
            _assistant("zero"),
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["context"] == 5 + 2_000 + 300


def test_scan_transcript_file_context_is_none_without_a_real_turn(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {"type": "user", "timestamp": "2024-01-01T10:00:00Z"},
            _assistant("synth", new=50, model="<synthetic>"),
        ],
    )
    assert claude_db._scan_transcript_file(path, project_by_folder={})["context"] is None


def test_scan_transcript_file_context_matches_the_live_gauge(tmp_path, write_transcript):
    import claude_context

    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            _assistant("m1", new=3, read=500, written=9_000),
            _assistant("side", new=77_777, isSidechain=True),
            _assistant("m2", new=4, read=9_500, written=120),
            _assistant("synth", new=1, model="<synthetic>"),
        ],
    )
    stored = claude_db._scan_transcript_file(path, project_by_folder={})["context"]
    live = claude_context.extract_turns(path.read_text(encoding="utf-8").splitlines())[-1].context
    assert stored == live == 4 + 9_500 + 120


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


def test_scan_transcript_file_stores_title_last_message_and_first_prompt_separately(
    tmp_path, write_transcript
):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "message": {"content": "Help me fix the login bug"},
            },
            {"type": "ai-title", "aiTitle": "Fix login bug"},
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:05:00Z",
                "message": {"content": [{"type": "text", "text": "Done, fixed it."}]},
            },
        ],
    )
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["title"] == "Fix login bug"
    assert row["last_message"] == "Done, fixed it."
    assert row["first_prompt"] == "Help me fix the login bug"


def test_scan_transcript_file_last_message_ignores_tool_only_turns(tmp_path, write_transcript):
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
            # A tool-only turn (no text block) must not blank out last_message.
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
    assert row["last_message"] == "Anything else?"
    assert row["title"] == ""


def test_scan_transcript_file_first_prompt_skips_command_only_first_message(
    tmp_path, write_transcript
):
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
    assert row["first_prompt"] == "Now the real question"


def test_scan_transcript_file_title_last_message_first_prompt_blank_when_no_content(
    tmp_path, write_transcript
):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(path, [{"type": "system", "timestamp": "2024-01-01T10:00:00Z"}])
    row = claude_db._scan_transcript_file(path, project_by_folder={})
    assert row["title"] == ""
    assert row["last_message"] == ""
    assert row["first_prompt"] == ""


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


def test_transcript_lookup_and_delete_by_project(isolated_db, write_config, write_transcript):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    write_transcript(
        tmp_path / "projects" / folder / "s1.jsonl",
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj"}],
    )
    claude_db.refresh()

    paths = claude_db.transcript_paths_for_project("/home/x/proj")
    assert len(paths) == 1
    assert paths[0] == tmp_path / "projects" / folder / "s1.jsonl"

    claude_db.delete_transcript_rows_by_project("/home/x/proj")
    assert claude_db.fetch_transcripts() == []


def test_transcript_lookup_and_delete_by_project_ignores_drifted_cwd(
    isolated_db, write_config, write_transcript
):
    """A session that `cd`'d partway through leaves `cwd` pointing below the project root -
    matching must still go by the on-disk folder, not the recorded `cwd`."""
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    write_transcript(
        tmp_path / "projects" / folder / "s1.jsonl",
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj/subdir"}],
    )
    claude_db.refresh()

    paths = claude_db.transcript_paths_for_project("/home/x/proj")
    assert len(paths) == 1
    assert paths[0] == tmp_path / "projects" / folder / "s1.jsonl"

    claude_db.delete_transcript_rows_by_project("/home/x/proj")
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


# ---------------------------------------------------------------------------
# history.db - durable store (schema, upsert, fetch)
# ---------------------------------------------------------------------------


def _history_row(session_id="s1", **overrides):
    row = {
        "session_id": session_id,
        "path": Path("/tmp/some/s1.jsonl"),
        "cwd": "/tmp/some",
        "version": "1.0.0",
        "git_branch": "main",
        "started_at": datetime(2024, 1, 1, 10, 0, 0),
        "updated_at": datetime(2024, 1, 1, 10, 5, 0),
        "message_count": 1,
        "cost": 0.01,
        "cost_source": "estimated",
        "unpriced_models": [],
        "cost_state_flagged": False,
        "context": 100,
        "project": "some",
        "title": "",
        "last_message": "",
        "first_prompt": "",
    }
    row.update(overrides)
    return row


def test_history_schema_creates_db_file_and_transcripts_table(isolated_db):
    with claude_db._connect_history() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert "transcripts" in tables
    assert claude_db.history_db_path().is_file()


def test_upsert_history_transcripts_is_a_noop_for_empty_rows(isolated_db):
    claude_db.upsert_history_transcripts([])
    assert claude_db.fetch_history_transcripts() == []


def test_upsert_history_transcripts_inserts_new_rows(isolated_db):
    claude_db.upsert_history_transcripts([_history_row("s1"), _history_row("s2")])
    rows = claude_db.fetch_history_transcripts()
    assert {row["session_id"] for row in rows} == {"s1", "s2"}


def test_upsert_history_transcripts_updates_existing_row_in_place(isolated_db):
    claude_db.upsert_history_transcripts([_history_row("s1", cost=0.01, message_count=1)])
    claude_db.upsert_history_transcripts([_history_row("s1", cost=0.05, message_count=3)])

    rows = claude_db.fetch_history_transcripts()
    assert len(rows) == 1
    assert rows[0]["session_id"] == "s1"
    assert rows[0]["cost"] == 0.05
    assert rows[0]["message_count"] == 3


def test_fetch_history_transcripts_returns_all_rows(isolated_db):
    claude_db.upsert_history_transcripts([_history_row("s1"), _history_row("s2")])
    rows = claude_db.fetch_history_transcripts()
    assert len(rows) == 2
    assert {row["session_id"] for row in rows} == {"s1", "s2"}


# ---------------------------------------------------------------------------
# fetch_transcripts() - merges live ledger.db rows with history.db's durable rows
# ---------------------------------------------------------------------------


def test_fetch_transcripts_includes_history_only_session(isolated_db, write_config):
    write_config(isolated_db / "claude.json", {})
    claude_db.refresh()  # no live transcripts on disk

    claude_db.upsert_history_transcripts([_history_row("history-only")])

    transcripts = claude_db.fetch_transcripts()
    assert [row["session_id"] for row in transcripts] == ["history-only"]


def test_fetch_transcripts_prefers_live_row_over_history_row(
    isolated_db, write_config, write_transcript
):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    write_transcript(
        tmp_path / "projects" / folder / "s1.jsonl",
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj", "sessionId": "s1"}],
    )
    claude_db.refresh()

    claude_db.upsert_history_transcripts([_history_row("s1", cost=999.0, message_count=999)])

    transcripts = claude_db.fetch_transcripts()
    assert len(transcripts) == 1
    assert transcripts[0]["session_id"] == "s1"
    assert transcripts[0]["message_count"] == 1
    assert transcripts[0]["cost"] == 0.0


# ---------------------------------------------------------------------------
# Delete propagation - deleting a session/project purges history.db too
# ---------------------------------------------------------------------------


def test_delete_transcript_row_purges_both_stores(isolated_db, write_config, write_transcript):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    write_transcript(
        tmp_path / "projects" / folder / "s1.jsonl",
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj", "sessionId": "s1"}],
    )
    claude_db.refresh()
    claude_db.upsert_history_transcripts([_history_row("s1")])

    claude_db.delete_transcript_row("s1")

    assert claude_db.fetch_transcripts() == []
    assert claude_db.fetch_history_transcripts() == []


def test_delete_transcript_row_purges_history_only_session(isolated_db, write_config):
    write_config(isolated_db / "claude.json", {})
    claude_db.refresh()
    claude_db.upsert_history_transcripts([_history_row("history-only")])

    claude_db.delete_transcript_row("history-only")

    assert claude_db.fetch_transcripts() == []
    assert claude_db.fetch_history_transcripts() == []


def test_transcript_path_for_session_falls_back_to_history(isolated_db, write_config):
    write_config(isolated_db / "claude.json", {})
    claude_db.refresh()
    claude_db.upsert_history_transcripts(
        [_history_row("history-only", path=Path("/tmp/some/history-only.jsonl"))]
    )

    assert claude_db.transcript_path_for_session("history-only") == Path(
        "/tmp/some/history-only.jsonl"
    )
    assert claude_db.transcript_path_for_session("nonexistent") is None


def test_delete_transcript_rows_by_project_purges_both_stores(
    isolated_db, write_config, write_transcript
):
    tmp_path = isolated_db
    write_config(tmp_path / "claude.json", {})
    folder = claude_db.sanitize_project_path("/home/x/proj")
    write_transcript(
        tmp_path / "projects" / folder / "s1.jsonl",
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/home/x/proj", "sessionId": "s1"}],
    )
    claude_db.refresh()
    claude_db.upsert_history_transcripts(
        [_history_row("s1", path=tmp_path / "projects" / folder / "s1.jsonl")]
    )

    claude_db.delete_transcript_rows_by_project("/home/x/proj")

    assert claude_db.fetch_transcripts() == []
    assert claude_db.fetch_history_transcripts() == []


def test_delete_transcript_rows_by_project_purges_history_only_sessions(isolated_db, write_config):
    """A project whose sessions are already pruned from disk and absent from ledger.db still
    has its history.db rows removed, matched by the same on-disk folder name."""
    write_config(isolated_db / "claude.json", {})
    claude_db.refresh()
    folder = claude_db.sanitize_project_path("/home/x/proj")
    claude_db.upsert_history_transcripts(
        [_history_row("history-only", path=Path(f"/whatever/{folder}/history-only.jsonl"))]
    )

    claude_db.delete_transcript_rows_by_project("/home/x/proj")

    assert claude_db.fetch_history_transcripts() == []


def _db_files(directory):
    return sorted(p.name for p in directory.glob("ledger.db*"))


def test_connect_uses_wal_mode(isolated_db):
    with claude_db._connect() as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_startup_leaves_no_db_files_after_exit_hook(isolated_db, monkeypatch):
    hooks = []
    monkeypatch.setattr(claude_db, "_started", False)
    monkeypatch.setattr(claude_db.atexit, "register", lambda fn, *a: hooks.append((fn, a)))
    # A stale snapshot from a previous run, WAL side files included, is wiped.
    for suffix in ("", "-wal", "-shm"):
        (isolated_db / f"ledger.db{suffix}").write_text("stale")

    claude_db.startup()
    assert claude_db.refreshed_at() is not None

    (fn, args), = hooks
    fn(*args)
    assert _db_files(isolated_db) == []


def test_read_succeeds_while_another_connection_holds_a_write_transaction(isolated_db):
    import sqlite3

    claude_db.refresh()
    writer = sqlite3.connect(claude_db.db_path())
    try:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("DELETE FROM transcripts")
        writer.executemany(
            "INSERT INTO transcripts (session_id, path, cwd, version, git_branch,"
            " message_count, cost, project) VALUES (?, '', '', '', '', 0, 0, '')",
            [(f"s{i}",) for i in range(5000)],
        )
        # Uncommitted: readers still see the last committed snapshot, no lock error.
        assert claude_db.refreshed_at() is not None
        assert claude_db.fetch_transcripts() == []
    finally:
        writer.rollback()
        writer.close()


def test_scan_transcript_file_detects_openspec_slash_command(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {
                "type": "user",
                "sessionId": "s",
                "message": {"content": "<command-name>/opsx:propose</command-name>"},
            }
        ],
    )
    assert claude_db._scan_transcript_file(path, project_by_folder={})["used_openspec"] is True


def test_scan_transcript_file_detects_openspec_skill_call(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [
            {
                "type": "assistant",
                "sessionId": "s",
                "message": {
                    "id": "m1",
                    "content": [
                        {"type": "tool_use", "name": "Skill", "input": {"skill": "openspec-apply-change"}}
                    ],
                },
            }
        ],
    )
    assert claude_db._scan_transcript_file(path, project_by_folder={})["used_openspec"] is True


def test_scan_transcript_file_without_openspec_is_false(tmp_path, write_transcript):
    path = tmp_path / "projects" / "f" / "abc.jsonl"
    write_transcript(
        path,
        [{"type": "user", "sessionId": "s", "message": {"content": "talk about /opsx:propose"}}],
    )
    assert claude_db._scan_transcript_file(path, project_by_folder={})["used_openspec"] is False
