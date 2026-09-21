import json

import pytest

import claude_context
from claude_context import (
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


# ---------------------------------------------------------------- 1.1 turn extraction


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


# ---------------------------------------------------------------- 1.2 humanising


@pytest.mark.parametrize("tokens, expected", [
    (0, "0"), (742, "742"), (999, "999"), (1_000, "1k"), (80_618, "81k"), (80_500, "81k"),
    (394_502, "395k"), (999_499, "999k"), (999_500, "1.0M"), (999_999, "1.0M"),
    (1_000_000, "1.0M"), (1_234_567, "1.2M"),
])
def test_humanise_tokens(tokens, expected):
    assert humanise_tokens(tokens) == expected


# ---------------------------------------------------------------- 1.3 growth and sparkline


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


# ---------------------------------------------------------------- 2.1 tail reader


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


# ---------------------------------------------------------------- 2.2 transcript location


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


# ---------------------------------------------------------------- 2.3 stat-keyed cache, 2.4 entry point


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


def test_live_context_never_raises(isolated_db, write_transcript, monkeypatch):
    assert live_context("missing", "/x/proj") is None

    _write_session(isolated_db, write_transcript, entries=[_assistant("m1", read=100)])

    def boom(_path):
        raise PermissionError("locked")

    monkeypatch.setattr(claude_context, "_read_tail_turns", boom)
    assert live_context("s1", "/x/proj") is None

    monkeypatch.setattr(claude_context, "_read_tail_turns", lambda _p: (_ for _ in ()).throw(UnicodeDecodeError("utf-8", b"", 0, 1, "bad")))
    assert live_context("s1", "/x/proj") is None


# ---------------------------------------------------------------- 4.1 full parse


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


# ---------------------------------------------------------------- 4.2 cache miss


def test_cache_miss_flags():
    detail = parse_detail(_lines(
        _assistant("m1", new=2, read=1_000, written=20_000),   # first response: never a miss
        _assistant("m2", new=2, read=150_000, written=500),    # normal cached response
        _assistant("m3", new=2, read=41_000, written=168_000),  # cache miss
    ))
    assert [t.cache_miss for t in detail.turns] == [False, False, True]


# ---------------------------------------------------------------- 4.3 growth attribution


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


# ---------------------------------------------------------------- 4.4 memoized full parse


def test_load_detail_is_memoized_by_file_stat(isolated_db, write_transcript, monkeypatch):
    path = _write_session(isolated_db, write_transcript, entries=[_assistant("m1", new=0, read=100)])
    calls = []
    real = claude_context.parse_detail
    monkeypatch.setattr(claude_context, "parse_detail", lambda lines: calls.append(1) or real(lines))

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
    monkeypatch.setattr(claude_context, "parse_detail", lambda _lines: (_ for _ in ()).throw(OSError("gone")))
    assert load_detail("s1", "/x/proj") is None
