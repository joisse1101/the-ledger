import json
from datetime import datetime, timezone

import pytest

from app.domain import claude_context
from app.domain.claude_context import (
    Compaction,
    LiveContext,
    ToolUse,
    Turn,
    attribute_growth,
    extract_turns,
    format_context,
    format_growth,
    humanise_tokens,
    live_context,
    load_detail,
    parse_detail,
    sparkline,
    transcript_path,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    for cache in (claude_context._located, claude_context._live_cache, claude_context._detail_cache):
        cache.clear()


def _assistant(message_id, *, new=2, read=0, written=0, output=10, tools=(), model="claude-sonnet-5",
               sidechain=False, content=None, timestamp="2026-09-18T04:12:10.124Z"):
    if content is None:
        content = [{"type": "tool_use", "name": name, "input": tool_input} for name, tool_input in tools]
    return {
        "type": "assistant",
        "isSidechain": sidechain,
        "timestamp": timestamp,
        "message": {
            "id": message_id,
            "model": model,
            "content": content,
            "usage": {
                "input_tokens": new,
                "cache_read_input_tokens": read,
                "cache_creation_input_tokens": written,
                "output_tokens": output,
            },
        },
    }


def _compact_boundary(pre_tokens=191736, trigger="manual"):
    return {"type": "system", "subtype": "compact_boundary",
            "compactMetadata": {"trigger": trigger, "preTokens": pre_tokens, "postTokens": 12681}}


def _lines(*entries):
    return [json.dumps(entry) for entry in entries]


def _turn(context, *tools, output=0):
    return Turn(message_id="m", timestamp=None, new=context, cache_read=0, cache_written=0, output=output,
                tools=list(tools))


# ---------------------------------------------------------------- turn extraction


def test_context_includes_cached_tokens():
    [turn] = extract_turns(_lines(_assistant("m1", new=2, read=393_000, written=1_500)))
    assert turn.context == 394_502


def test_multi_block_turn_is_deduplicated_and_last_usage_wins():
    lines = _lines(
        _assistant("m1", new=2, read=100, output=5, content=[{"type": "thinking", "thinking": ""}]),
        _assistant("m1", new=2, read=100, output=300, tools=[("Read", {"file_path": "a.py"})]),
        _assistant("m2", new=2, read=500),
    )
    turns = extract_turns(lines)
    assert [t.message_id for t in turns] == ["m1", "m2"]
    assert turns[0].output == 300
    assert turns[0].tools == [ToolUse("Read", "a.py")]


def test_tools_accumulate_across_a_turns_lines():
    lines = _lines(
        _assistant("m1", read=10, tools=[("Read", {"file_path": "a.py"})]),
        _assistant("m1", read=10, tools=[("Bash", {"command": "ls"})]),
    )
    [turn] = extract_turns(lines)
    assert [t.name for t in turn.tools] == ["Read", "Bash"]


def test_synthetic_and_zero_usage_turns_are_skipped():
    lines = _lines(
        _assistant("m1", new=0, read=210_000),
        _assistant("m2", new=0, read=0, written=0, output=0, model="<synthetic>"),
        _assistant("m3", new=0, read=0, written=0, output=0),
    )
    assert [t.context for t in extract_turns(lines)] == [210_000]


def test_sidechain_turns_are_skipped():
    lines = _lines(_assistant("m1", new=0, read=1_000), _assistant("m2", new=0, read=90_000, sidechain=True))
    assert [t.context for t in extract_turns(lines)] == [1_000]


def test_malformed_and_non_assistant_lines_are_skipped():
    lines = ["not json", "[]", json.dumps({"type": "user"}), json.dumps({"type": "assistant", "message": "x"}),
             json.dumps(_assistant("m1", read=7))]
    assert [t.context for t in extract_turns(lines)] == [9]


def test_tool_hint_prefers_path_then_command_and_is_single_line_and_short():
    lines = _lines(_assistant("m1", read=1, tools=[
        ("Read", {"file_path": "/x/y.py", "offset": 3}),
        ("Bash", {"command": "echo a\n  echo b"}),
        ("Long", {"command": "x" * 200}),
        ("None", {"foo": 1}),
    ]))
    [turn] = extract_turns(lines)
    assert turn.tools[0].hint == "/x/y.py"
    assert turn.tools[1].hint == "echo a echo b"
    assert len(turn.tools[2].hint) == 80 and turn.tools[2].hint.endswith("…")
    assert turn.tools[3].hint == ""


# ---------------------------------------------------------------- humanising


@pytest.mark.parametrize("tokens, expected", [
    (0, "0"), (742, "742"), (999, "999"), (1_000, "1k"), (80_618, "81k"), (80_500, "81k"),
    (394_502, "395k"), (999_499, "999k"), (999_500, "1.0M"), (999_999, "1.0M"),
    (1_000_000, "1.0M"), (1_234_567, "1.2M"),
])
def test_humanise_tokens(tokens, expected):
    assert humanise_tokens(tokens) == expected


# ---------------------------------------------------------------- growth and sparkline


@pytest.mark.parametrize("delta, expected", [
    (2_100, "▲ +2.1k"), (400, "▲ +400"), (12_345, "▲ +12.3k"), (-2_100, "▼ -2.1k"), (-50, "▼ -50"),
    (999_990, "▲ +1.0M"), (0, "• 0"),
])
def test_format_growth(delta, expected):
    assert format_growth(delta) == expected


def test_sparkline_is_scaled_from_zero_so_slow_growth_looks_flat():
    glyphs = sparkline([390_000, 391_000, 392_000, 394_000])
    assert set(glyphs) <= {"▇", "█"}


def test_sparkline_rises_from_the_baseline():
    assert sparkline([0, 50, 100]) == "▁▅█"
    assert sparkline([]) == ""


def test_format_context_full_cell():
    cell = format_context(LiveContext(size=394_000, growth=2_100, history=[390_000, 391_900, 394_000]))
    assert cell.startswith("394k ▲ +2.1k ")
    assert len(cell.split(" ")[-1]) == 3


def test_format_context_shrink_shows_downward_marker_and_decrease():
    cell = format_context(LiveContext(size=60_000, growth=-330_000, history=[390_000, 60_000]))
    assert cell.startswith("60k ▼ -330.0k ")


def test_format_context_single_response_is_size_only():
    assert format_context(LiveContext(size=42_000, growth=None, history=[42_000])) == "42k"


# ---------------------------------------------------------------- tail reader


def test_tail_reader_skips_a_trailing_partial_line(tmp_path):
    path = tmp_path / "s.jsonl"
    complete = "\n".join(_lines(_assistant("m1", read=100), _assistant("m2", read=200)))
    path.write_text(complete + '\n{"type": "assistant", "message": {"id": "m3", "usa', encoding="utf-8")
    assert [t.context for t in claude_context._read_tail_turns(path)] == [102, 202]


def test_tail_reader_on_an_empty_file(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text("", encoding="utf-8")
    assert claude_context._read_tail_turns(path) == []


def test_tail_reader_doubles_its_window_past_an_oversized_line(tmp_path, write_transcript):
    path = tmp_path / "s.jsonl"
    big = _assistant("m2", read=200)
    big["message"]["content"] = [{"type": "text", "text": "x" * (claude_context._TAIL_WINDOW * 3)}]
    write_transcript(path, [_assistant("m1", read=100), big, {"type": "user", "message": {"content": "hi"}}])
    assert [t.context for t in claude_context._read_tail_turns(path)] == [102, 202]


def test_tail_reader_caps_at_the_requested_turn_count(tmp_path, write_transcript):
    path = tmp_path / "s.jsonl"
    write_transcript(path, [_assistant(f"m{i}", new=0, read=i + 1) for i in range(40)])
    turns = claude_context._read_tail_turns(path, limit=24)
    assert [t.context for t in turns] == list(range(17, 41))


def test_tail_reader_drops_the_first_line_of_a_window_that_starts_mid_file(tmp_path, write_transcript, monkeypatch):
    path = tmp_path / "s.jsonl"
    write_transcript(path, [_assistant(f"m{i}", new=0, read=1000 + i) for i in range(50)])
    monkeypatch.setattr(claude_context, "_TAIL_WINDOW", 700)
    turns = claude_context._read_tail_turns(path, limit=3)
    assert [t.context for t in turns] == [1047, 1048, 1049]


# ---------------------------------------------------------------- transcript location


def test_transcript_path_uses_the_sanitized_cwd(isolated_db, write_transcript):
    projects = isolated_db / "projects"
    path = projects / claude_context.claude_db.sanitize_project_path("C:\\Users\\me\\proj") / "s1.jsonl"
    write_transcript(path, [_assistant("m1", read=1)])
    assert transcript_path("s1", "C:\\Users\\me\\proj") == path


def test_transcript_path_falls_back_to_a_memoized_glob(isolated_db, write_transcript):
    path = isolated_db / "projects" / "some-other-folder" / "s1.jsonl"
    write_transcript(path, [_assistant("m1", read=1)])
    assert transcript_path("s1", "/not/where/it/is") == path
    assert claude_context._located == {"s1": path}
    assert transcript_path("s1", "/not/where/it/is") == path


def test_transcript_path_missing(isolated_db):
    assert transcript_path("nope", "/x") is None
    assert claude_context._located == {}


# ---------------------------------------------------------------- stat-keyed cache, entry point


def _write_session(isolated_db, write_transcript, session_id="s1", cwd="/x/proj", entries=()):
    path = isolated_db / "projects" / claude_context.claude_db.sanitize_project_path(cwd) / f"{session_id}.jsonl"
    write_transcript(path, list(entries))
    return path


def test_live_context_size_growth_and_history(isolated_db, write_transcript):
    _write_session(isolated_db, write_transcript, entries=[
        _assistant("m1", new=2, read=1_000, written=500),
        _assistant("m2", new=2, read=2_000, written=1_600),
    ])
    assert live_context("s1", "/x/proj") == LiveContext(size=3_602, growth=2_100, history=[1_502, 3_602])


def test_live_context_single_response_has_no_growth(isolated_db, write_transcript):
    _write_session(isolated_db, write_transcript, entries=[_assistant("m1", read=5_000)])
    result = live_context("s1", "/x/proj")
    assert result is not None and result.growth is None and result.history == [5_002]


def test_live_context_ignores_a_trailing_error_placeholder(isolated_db, write_transcript):
    _write_session(isolated_db, write_transcript, entries=[
        _assistant("m1", new=0, read=210_000),
        _assistant("m2", new=0, model="<synthetic>", output=0),
    ])
    result = live_context("s1", "/x/proj")
    assert result is not None and result.size == 210_000


def test_live_context_with_no_real_response_is_none(isolated_db, write_transcript):
    _write_session(isolated_db, write_transcript, entries=[{"type": "user", "message": {"content": "hi"}}])
    assert live_context("s1", "/x/proj") is None


def test_live_context_reads_an_unchanged_file_once_and_again_after_an_append(isolated_db, write_transcript, monkeypatch):
    path = _write_session(isolated_db, write_transcript, entries=[_assistant("m1", new=0, read=100)])
    calls = []
    real = claude_context._read_tail_turns
    monkeypatch.setattr(claude_context, "_read_tail_turns", lambda p: calls.append(p) or real(p))

    assert live_context("s1", "/x/proj").size == 100
    assert live_context("s1", "/x/proj").size == 100
    assert len(calls) == 1

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_assistant("m2", new=0, read=250)) + "\n")
    assert live_context("s1", "/x/proj").size == 250
    assert len(calls) == 2


def test_latest_activity_is_the_newest_user_line_timestamp(isolated_db, write_transcript):
    _write_session(isolated_db, write_transcript, entries=[
        {"type": "user", "timestamp": "2026-01-01T12:00:01Z"},
        {"type": "user", "timestamp": "2026-01-01T12:00:05Z"},
        {"type": "summary"},  # no timestamp
    ])
    assert claude_context.latest_activity("s1", "/x/proj") == datetime(2026, 1, 1, 12, 0, 5, tzinfo=timezone.utc)


def test_latest_activity_ignores_assistant_and_bookkeeping_lines(isolated_db, write_transcript):
    # A dialog can be open while these are written (a later tool call of the same batch still
    # streaming in, an attachment or system note), so they must not read as "the prompt was answered".
    _write_session(isolated_db, write_transcript, entries=[
        {"type": "user", "timestamp": "2026-01-01T12:00:01Z"},
        {"type": "assistant", "timestamp": "2026-01-01T12:00:05Z"},
        {"type": "attachment", "timestamp": "2026-01-01T12:00:06Z"},
        {"type": "system", "subtype": "hook_progress", "timestamp": "2026-01-01T12:00:07Z"},
        {"type": "progress", "timestamp": "2026-01-01T12:00:08Z"},
    ])
    assert claude_context.latest_activity("s1", "/x/proj") == datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc)


def test_latest_activity_is_none_when_the_transcript_has_no_user_line(isolated_db, write_transcript):
    _write_session(isolated_db, write_transcript, entries=[{"type": "assistant", "timestamp": "2026-01-01T12:00:05Z"}])
    assert claude_context.latest_activity("s1", "/x/proj") is None


def test_latest_activity_reads_an_unchanged_file_once_and_again_after_an_append(isolated_db, write_transcript, monkeypatch):
    path = _write_session(isolated_db, write_transcript, entries=[{"type": "user", "timestamp": "2026-01-01T12:00:01Z"}])
    calls = []
    real = claude_context._read_tail_latest_timestamp
    monkeypatch.setattr(claude_context, "_read_tail_latest_timestamp", lambda p: calls.append(p) or real(p))

    claude_context.latest_activity("s1", "/x/proj")
    claude_context.latest_activity("s1", "/x/proj")
    assert len(calls) == 1

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "timestamp": "2026-01-01T12:00:09Z"}) + "\n")
    assert claude_context.latest_activity("s1", "/x/proj") == datetime(2026, 1, 1, 12, 0, 9, tzinfo=timezone.utc)
    assert len(calls) == 2


def test_latest_activity_widens_its_window_past_an_oversized_untimestamped_line(isolated_db, write_transcript, monkeypatch):
    _write_session(isolated_db, write_transcript, entries=[
        {"type": "user", "timestamp": "2026-01-01T12:00:01Z"},
        {"type": "user", "blob": "x" * 5_000},
    ])
    monkeypatch.setattr(claude_context, "_TAIL_WINDOW", 700)
    assert claude_context.latest_activity("s1", "/x/proj") == datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc)


def test_latest_activity_treats_a_naive_timestamp_as_utc(isolated_db, write_transcript):
    _write_session(isolated_db, write_transcript, entries=[{"type": "user", "timestamp": "2026-01-01T12:00:01"}])
    assert claude_context.latest_activity("s1", "/x/proj") == datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc)


def test_latest_activity_is_none_when_missing_empty_or_untimestamped(isolated_db, write_transcript):
    assert claude_context.latest_activity("missing", "/x/proj") is None
    _write_session(isolated_db, write_transcript, entries=[{"type": "summary"}])
    assert claude_context.latest_activity("s1", "/x/proj") is None


def test_live_context_never_raises(isolated_db, write_transcript, monkeypatch):
    assert live_context("missing", "/x/proj") is None

    _write_session(isolated_db, write_transcript, entries=[_assistant("m1", read=100)])

    def boom(_path):
        raise PermissionError("locked")

    monkeypatch.setattr(claude_context, "_read_tail_turns", boom)
    assert live_context("s1", "/x/proj") is None

    monkeypatch.setattr(claude_context, "_read_tail_turns", lambda _p: (_ for _ in ()).throw(UnicodeDecodeError("utf-8", b"", 0, 1, "bad")))
    assert live_context("s1", "/x/proj") is None


# ---------------------------------------------------------------- full parse


def test_parse_detail_orders_turns_and_positions_compactions():
    detail = parse_detail(_lines(
        _assistant("m1", new=1, read=10, written=20, output=5, timestamp="2026-09-18T04:00:00Z"),
        _assistant("m2", new=2, read=30, written=40, output=6),
        _compact_boundary(pre_tokens=99_000),
        _assistant("m3", new=3, read=50, written=60, output=7),
    ))
    assert [(t.new, t.cache_read, t.cache_written, t.output) for t in detail.turns] == [
        (1, 10, 20, 5), (2, 30, 40, 6), (3, 50, 60, 7)]
    assert detail.turns[0].timestamp is not None and detail.turns[0].timestamp.year == 2026
    assert detail.compactions == [Compaction(position=2, trigger="manual", pre_tokens=99_000)]


def test_parse_detail_without_compaction():
    detail = parse_detail(_lines(_assistant("m1", read=10)))
    assert detail.compactions == []


# ---------------------------------------------------------------- cache miss


def test_cache_miss_flags():
    detail = parse_detail(_lines(
        _assistant("m1", new=2, read=1_000, written=20_000),   # first response: never a miss
        _assistant("m2", new=2, read=150_000, written=500),    # normal cached response
        _assistant("m3", new=2, read=41_000, written=168_000),  # cache miss
    ))
    assert [t.cache_miss for t in detail.turns] == [False, False, True]


# ---------------------------------------------------------------- growth attribution


def test_attribution_reconciles_and_groups_by_tool():
    turns = [
        _turn(50_000, ToolUse("Read", "a.py")),
        _turn(60_000, ToolUse("Bash", "ls"), ToolUse("Read", "b.py")),
        _turn(65_000),
        _turn(80_000, ToolUse("Read", "c.py")),
        _turn(81_000),
    ]
    attribution = attribute_growth(turns, [])
    assert attribution.floor == 50_000 and attribution.current == 81_000
    assert attribution.floor + sum(g.tokens for g in attribution.by_tool) == attribution.current

    by_tool = {g.tool: g for g in attribution.by_tool}
    assert (by_tool["Read"].tokens, by_tool["Read"].uses) == (11_000, 2)
    assert (by_tool["Bash"].tokens, by_tool["Bash"].uses) == (5_000, 1)
    assert (by_tool["prompt / text"].tokens, by_tool["prompt / text"].uses) == (15_000, 1)
    assert [g.tool for g in attribution.by_tool] == ["prompt / text", "Read", "Bash"]


def test_attribution_lists_the_five_largest_increases_with_hints():
    contexts = [1_000, 1_100, 1_900, 2_000, 2_900, 3_000, 4_500, 4_600, 5_000]
    turns = [_turn(c, ToolUse("Read", f"f{i}.py")) for i, c in enumerate(contexts)]
    largest = attribute_growth(turns, []).largest
    assert [inc.tokens for inc in largest] == [1_500, 900, 800, 400, 100]
    assert [inc.index for inc in largest] == [6, 4, 2, 8, 1]
    assert (largest[0].tool, largest[0].hint) == ("Read", "f5.py")  # the previous response's tool


def test_attribution_ties_keep_chronological_order():
    turns = [_turn(0, ToolUse("A")), _turn(100, ToolUse("B")), _turn(200, ToolUse("C")), _turn(300)]
    assert [(inc.index, inc.tool) for inc in attribute_growth(turns, []).largest] == [(1, "A"), (2, "B"), (3, "C")]


def test_attribution_reconciles_when_context_shrinks_without_a_compaction():
    turns = [_turn(100_000, ToolUse("Read")), _turn(120_000, ToolUse("Bash")), _turn(70_000), _turn(75_000)]
    attribution = attribute_growth(turns, [])
    assert attribution.floor + sum(g.tokens for g in attribution.by_tool) == attribution.current == 75_000
    assert [inc.tokens for inc in attribution.largest] == [20_000, 5_000]  # only growth is listed


def test_attribution_restarts_after_the_latest_compaction():
    turns = [_turn(100_000, ToolUse("Read")), _turn(300_000, ToolUse("Bash")), _turn(310_000),
             _turn(60_000, ToolUse("Grep")), _turn(64_000)]
    attribution = attribute_growth(turns, [Compaction(position=3)])
    assert attribution.floor == 60_000 and attribution.current == 64_000
    assert [(g.tool, g.tokens, g.uses) for g in attribution.by_tool] == [("Grep", 4_000, 1)]


def test_attribution_uses_only_the_most_recent_of_several_compactions():
    turns = [_turn(10), _turn(20), _turn(5), _turn(8)]
    attribution = attribute_growth(turns, [Compaction(position=1), Compaction(position=2)])
    assert (attribution.floor, attribution.current) == (5, 8)


def test_attribution_with_nothing_after_a_compaction_is_empty():
    attribution = attribute_growth([_turn(10), _turn(20)], [Compaction(position=2)])
    assert attribution.by_tool == [] and attribution.largest == []


def test_attribution_of_a_single_turn_has_no_growth():
    attribution = attribute_growth([_turn(10)], [])
    assert (attribution.floor, attribution.current, attribution.by_tool) == (10, 10, [])


# ---------------------------------------------------------------- memoized full parse


def test_load_detail_is_memoized_by_file_stat(isolated_db, write_transcript, monkeypatch):
    path = _write_session(isolated_db, write_transcript, entries=[_assistant("m1", new=0, read=100)])
    calls = []
    real = claude_context.parse_detail
    monkeypatch.setattr(claude_context, "parse_detail", lambda lines, session_id="": calls.append(1) or real(lines, session_id))

    assert len(load_detail("s1", "/x/proj").turns) == 1
    assert len(load_detail("s1", "/x/proj").turns) == 1
    assert len(calls) == 1

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_assistant("m2", new=0, read=250)) + "\n")
    assert len(load_detail("s1", "/x/proj").turns) == 2
    assert len(calls) == 2


def test_load_detail_missing_or_unreadable_is_none(isolated_db, write_transcript, monkeypatch):
    assert load_detail("missing", "/x/proj") is None

    _write_session(isolated_db, write_transcript, entries=[_assistant("m1", read=100)])
    monkeypatch.setattr(claude_context, "parse_detail", lambda *_args: (_ for _ in ()).throw(OSError("gone")))
    assert load_detail("s1", "/x/proj") is None


# ---------------------------------------------------------------- startup attachments (recorded shapes)
# Shapes observed in real transcripts (401 sessions): no removal field was ever non-empty, `instructions`
# is re-emitted after a compaction, and later `skill_listing` entries hold only the newly added skills.


def _instructions(*files, changed=None):
    """`files` are (path, type, content); type is User, Project or AutoMem."""
    entry = {"type": "instructions",
             "files": [{"path": path, "type": kind, "content": content} for path, kind, content in files]}
    if changed is not None:
        entry.update(changed=True, reason="session_start")
    return {"type": "attachment", "attachment": entry}


def _skill_listing(*skills, initial=False):
    """`skills` are (name, description); the content is one `- name: description` line each."""
    return {"type": "attachment", "attachment": {
        "type": "skill_listing", "isInitial": initial, "skillCount": len(skills),
        "names": [name for name, _ in skills],
        "content": "\n".join(f"- {name}: {text}" for name, text in skills)}}


def _agent_listing(*agents, initial=False, removed=()):
    """`agents` are (type, description)."""
    return {"type": "attachment", "attachment": {
        "type": "agent_listing_delta", "isInitial": initial, "builtInTypes": [], "showConcurrencyNote": False,
        "addedTypes": [name for name, _ in agents], "removedTypes": list(removed),
        "addedLines": [f"- {name}: {text}" for name, text in agents]}}


def _mcp_instructions(*servers, removed=()):
    """`servers` are (name, instructions); the block is `## name` then the instructions."""
    return {"type": "attachment", "attachment": {
        "type": "mcp_instructions_delta", "addedNames": [name for name, _ in servers],
        "addedBlocks": [f"## {name}\n{text}" for name, text in servers], "removedNames": list(removed)}}


def test_startup_attachments_do_not_disturb_the_existing_scan():
    entries = [
        _instructions(("/home/me/CLAUDE.md", "Project", "rules"), changed=True),
        _skill_listing(("review", "Review code"), initial=True),
        _agent_listing(("explorer", "Searches"), initial=True),
        _mcp_instructions(("docs", "Use the docs tool")),
        _assistant("m1", read=100),
        _skill_listing(("deploy", "Ship it")),
        _assistant("m2", read=150),
    ]

    turns, compactions, events = claude_context._scan(_lines(*entries))

    assert [turn.context for turn in turns] == [102, 152]  # `_assistant` adds new=2
    assert compactions == []


# ---------------------------------------------------------------- startup events


def _events(*entries):
    return claude_context._scan(_lines(*entries))[2]


def test_each_attachment_kind_becomes_one_event_at_the_current_turn_count():
    events = _events(
        _instructions(("C:\\Users\\me\\proj\\CLAUDE.md", "Project", "abcd")),
        _skill_listing(("review", "Review code"), ("deploy", "Ship it"), initial=True),
        _agent_listing(("explorer", "Searches"), initial=True),
        _mcp_instructions(("docs", "Use it")),
        _assistant("m1", read=10),
        _skill_listing(("late", "Added later")),
    )

    assert [(e.position, e.category) for e in events] == [
        (0, "memory"), (0, "skills"), (0, "agents"), (0, "mcp"), (1, "skills")]
    memory, skills, agents, mcp, late = events
    assert [(i.key, i.label) for i in memory.added] == [("C:\\Users\\me\\proj\\CLAUDE.md", "proj/CLAUDE.md")]
    assert [i.key for i in skills.added] == ["review", "deploy"] and skills.replace
    assert [i.key for i in agents.added] == ["explorer"] and agents.replace
    assert [(i.key, i.text) for i in mcp.added] == [("docs", "## docs\nUse it")]
    assert [i.key for i in late.added] == ["late"] and not late.replace


def test_removals_are_collected_when_recorded():
    events = _events(_agent_listing(removed=["explorer"]), _mcp_instructions(removed=["docs"]))

    assert [(e.category, e.removed) for e in events] == [("agents", ("explorer",)), ("mcp", ("docs",))]


def test_malformed_and_unrelated_attachments_are_skipped():
    events = _events(
        {"type": "attachment", "attachment": "nope"},
        {"type": "attachment"},
        {"type": "attachment", "attachment": {"type": "instructions", "files": [{"path": 3, "content": "x"}, "x"]}},
        {"type": "attachment", "attachment": {"type": "skill_listing", "content": None}},
        {"type": "attachment", "attachment": {"type": "deferred_tools_delta", "addedNames": ["Read"]}},
        {"type": "attachment", "isSidechain": True,
         "attachment": _skill_listing(("sub", "Subagent"))["attachment"]},
        _skill_listing(("kept", "Fine")),
    )

    assert [i.key for e in events for i in e.added] == ["kept"]


def test_a_multi_line_skill_description_stays_one_item():
    [event] = _events(_skill_listing(("a", "first line\n  continued"), ("b", "other")))

    assert [i.key for i in event.added] == ["a", "b"]
    assert "continued" in event.added[0].text


# ---------------------------------------------------------------- startup snapshots


def _category(snapshot, name):
    return next((c for c in snapshot.categories if c.name == name), None)


def test_estimates_are_a_quarter_of_the_characters_rounded_up():
    assert claude_context.estimate_tokens("") == 0
    assert claude_context.estimate_tokens("abcd") == 1
    assert claude_context.estimate_tokens("abcde") == 2


def test_items_sum_to_their_category_and_are_largest_first():
    breakdown = parse_detail(_lines(
        _skill_listing(("small", "x" * 6), ("big", "y" * 94), initial=True),
        _assistant("m1", read=10_000),
    )).breakdown

    [snapshot] = breakdown.snapshots
    skills = _category(snapshot, "Skills")
    assert [item.label for item in skills.items] == ["big", "small"]
    assert skills.tokens == sum(item.tokens for item in skills.items)


def test_a_skill_added_after_the_third_response_appears_from_the_fourth():
    breakdown = parse_detail(_lines(
        _skill_listing(("first", "x" * 40), initial=True),
        _assistant("m1", read=5_000), _assistant("m2", read=5_000), _assistant("m3", read=5_000),
        _skill_listing(("second", "y" * 40)),
        _assistant("m4", read=5_000),
    )).breakdown

    assert [s.position for s in breakdown.snapshots] == [0, 3]
    assert [t.snapshot for t in breakdown.turns] == [0, 0, 0, 1]
    assert [i.label for i in _category(breakdown.snapshots[0], "Skills").items] == ["first"]
    assert {i.label for i in _category(breakdown.snapshots[1], "Skills").items} == {"first", "second"}


def test_a_removed_agent_leaves_later_snapshots_and_an_unrecorded_category_is_absent():
    breakdown = parse_detail(_lines(
        _agent_listing(("keep", "k" * 40), ("drop", "d" * 40), initial=True),
        _assistant("m1", read=5_000),
        _agent_listing(removed=["drop"]),
        _assistant("m2", read=5_000),
    )).breakdown

    first, second = breakdown.snapshots
    assert {i.label for i in _category(first, "Custom agents").items} == {"keep", "drop"}
    assert [i.label for i in _category(second, "Custom agents").items] == ["keep"]
    assert _category(second, "Skills") is None and _category(second, "MCP instructions") is None


def test_an_identical_reemitted_instructions_entry_adds_no_snapshot():
    memory = _instructions(("/p/CLAUDE.md", "Project", "z" * 40))
    breakdown = parse_detail(_lines(memory, _assistant("m1", read=5_000), memory, _assistant("m2", read=5_000))).breakdown

    assert len(breakdown.snapshots) == 1


def test_memory_files_merge_by_path_and_a_later_entry_replaces_the_same_path():
    breakdown = parse_detail(_lines(
        _instructions(("/a/CLAUDE.md", "Project", "a" * 40), ("/u/RULES.md", "User", "u" * 40)),
        _assistant("m1", read=5_000),
        _instructions(("/a/CLAUDE.md", "Project", "a" * 400), changed=True),
        _assistant("m2", read=5_000),
    )).breakdown

    second = _category(breakdown.snapshots[1], "Memory files")
    assert {i.label: i.tokens for i in second.items} == {"a/CLAUDE.md": 100, "u/RULES.md": 10}


# ---------------------------------------------------------------- per-response breakdown


def _assert_rows_sum(detail):
    for row, turn in zip(detail.breakdown.turns, detail.turns):
        startup = sum(c.tokens for c in detail.breakdown.snapshots[row.snapshot].categories)
        assert startup + sum(g.tokens for g in row.growth) + row.remainder == turn.context
        assert row.remainder >= 0


def test_every_response_sums_to_its_context_and_growth_is_exact_by_tool():
    detail = parse_detail(_lines(
        _skill_listing(("s", "x" * 400), initial=True),
        _assistant("m1", new=0, read=1_000, tools=[("Read", {})]),
        _assistant("m2", new=0, read=1_300, tools=[("Bash", {})]),
        _assistant("m3", new=0, read=1_900, tools=[("Read", {})]),
        _assistant("m4", new=0, read=2_000),
    ))

    _assert_rows_sum(detail)
    assert detail.breakdown.turns[0].growth == []
    assert {g.tool: g.tokens for g in detail.breakdown.turns[-1].growth} == {"Read": 400, "Bash": 600}


def test_growth_matches_the_attribution_totals():
    detail = parse_detail(_lines(
        _assistant("m1", new=0, read=1_000, tools=[("Read", {})]),
        _assistant("m2", new=0, read=1_300, tools=[("Bash", {})]),
        _assistant("m3", new=0, read=1_900),
    ))

    final = {g.tool: g.tokens for g in detail.breakdown.turns[-1].growth}
    assert final == {g.tool: g.tokens for g in detail.attribution.by_tool}


def test_estimates_larger_than_the_first_response_are_scaled_down_and_the_remainder_is_zero():
    detail = parse_detail(_lines(
        _skill_listing(("a", "x" * 4_000), ("b", "y" * 4_000), initial=True),  # ~2,000 tokens estimated
        _assistant("m1", new=0, read=500),
    ))

    [snapshot] = detail.breakdown.snapshots
    assert sum(c.tokens for c in snapshot.categories) <= 500
    assert detail.breakdown.turns[0].remainder == 500 - sum(c.tokens for c in snapshot.categories)
    _assert_rows_sum(detail)


def test_breakdown_restarts_after_a_compaction_and_the_summary_lands_in_the_remainder():
    detail = parse_detail(_lines(
        _skill_listing(("s", "x" * 400), initial=True),
        _assistant("m1", new=0, read=1_000, tools=[("Read", {})]),
        _assistant("m2", new=0, read=5_000),
        _compact_boundary(),
        _assistant("m3", new=0, read=1_500, tools=[("Bash", {})]),
        _assistant("m4", new=0, read=1_800),
    ))

    _assert_rows_sum(detail)
    rows = detail.breakdown.turns
    assert rows[2].growth == []  # first response of the new segment
    assert {g.tool: g.tokens for g in rows[3].growth} == {"Bash": 300}
    assert rows[2].remainder > rows[0].remainder  # the summary is not startup content


def test_startup_state_carries_across_a_compaction():
    breakdown = parse_detail(_lines(
        _skill_listing(("s", "x" * 400), initial=True),
        _assistant("m1", new=0, read=1_000),
        _compact_boundary(),
        _assistant("m2", new=0, read=1_200),
    )).breakdown

    after = breakdown.snapshots[breakdown.turns[1].snapshot]
    assert [i.label for i in _category(after, "Skills").items] == ["s"]


def test_no_startup_content_leaves_growth_and_a_remainder_only():
    detail = parse_detail(_lines(
        _assistant("m1", new=0, read=1_000, tools=[("Read", {})]), _assistant("m2", new=0, read=1_400)))

    assert detail.breakdown.snapshots == [claude_context.StartupSnapshot(0, [])]
    assert [t.remainder for t in detail.breakdown.turns] == [1_000, 1_000]
    assert detail.breakdown.turns[1].growth == [claude_context.GrowthRow("Read", 400)]


def test_a_shrinking_context_without_compaction_still_sums():
    detail = parse_detail(_lines(
        _assistant("m1", new=0, read=2_000, tools=[("Read", {})]), _assistant("m2", new=0, read=1_500)))

    _assert_rows_sum(detail)
    assert detail.breakdown.turns[1].growth == [claude_context.GrowthRow("Read", -500)]


def test_a_failing_breakdown_is_dropped_and_logged_with_the_session_id(monkeypatch, caplog):
    monkeypatch.setattr(claude_context, "build_breakdown", lambda *_a: (_ for _ in ()).throw(KeyError("odd")))

    with caplog.at_level("WARNING", logger="ledger"):
        detail = parse_detail(_lines(_assistant("m1", read=10)), "sess-42")

    assert detail.breakdown is None and len(detail.turns) == 1
    assert "sess-42" in caplog.text


def test_an_empty_transcript_has_an_empty_breakdown():
    assert parse_detail([]).breakdown == claude_context.Breakdown(snapshots=[], turns=[])
