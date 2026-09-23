from datetime import datetime
from pathlib import Path

import pytest

import transcript_query as tq
from claude_transcripts import ClaudeTranscript


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
    return ClaudeTranscript(**defaults)  # type: ignore[arg-type]


def _ids(transcripts):
    return [t.session_id for t in transcripts]


# ---------------------------------------------------------------- search


def test_search_matches_session_id_last_message_and_first_prompt_case_insensitively():
    rows = [
        _transcript(session_id="abc-123", last_message="", first_prompt=""),
        _transcript(session_id="b", last_message="Deployed to STAGING", first_prompt=""),
        _transcript(session_id="c", last_message="", first_prompt="please refactor staging"),
        _transcript(session_id="d", last_message="unrelated", first_prompt="unrelated"),
    ]
    assert _ids(tq.filter_transcripts(rows, search="ABC-1")) == ["abc-123"]
    assert _ids(tq.filter_transcripts(rows, search="staging")) == ["b", "c"]


def test_search_does_not_look_at_the_title():
    rows = [_transcript(session_id="a", title="needle", last_message="", first_prompt="")]
    assert tq.filter_transcripts(rows, search="needle") == []


def test_search_is_literal_not_a_pattern():
    rows = [
        _transcript(session_id="dot", last_message="see a.b here"),
        _transcript(session_id="x", last_message="see axb here"),
    ]
    assert _ids(tq.filter_transcripts(rows, search="a.b")) == ["dot"]
    # Regex/wildcard characters are just text, and must not raise.
    assert tq.filter_transcripts(rows, search="(") == []
    assert tq.filter_transcripts(rows, search=".*") == []


# ---------------------------------------------------------------- filters


def test_filters_combine_with_and_and_match_any_selected_value():
    rows = [
        _transcript(session_id="1", project="a", git_branch="main", version="1"),
        _transcript(session_id="2", project="a", git_branch="dev", version="1"),
        _transcript(session_id="3", project="b", git_branch="main", version="2"),
        _transcript(session_id="4", project="c", git_branch="main", version="2"),
    ]
    assert _ids(tq.filter_transcripts(rows, projects=["a"], branches=["main"])) == ["1"]
    assert _ids(tq.filter_transcripts(rows, projects=["a", "b"], branches=["main"])) == ["1", "3"]
    assert _ids(tq.filter_transcripts(rows, versions=["2"], projects=["b"])) == ["3"]


def test_no_filters_returns_everything_in_order():
    rows = [_transcript(session_id="1"), _transcript(session_id="2")]
    assert _ids(tq.filter_transcripts(rows)) == ["1", "2"]


def test_filter_options_are_distinct_sorted_and_skip_blanks():
    rows = [
        _transcript(project="b", version="2", git_branch="main"),
        _transcript(project="a", version="2", git_branch=""),
        _transcript(project="b", version="", git_branch="dev"),
    ]
    assert tq.filter_options(rows) == {
        "projects": ["a", "b"],
        "versions": ["2"],
        "branches": ["dev", "main"],
    }


# ---------------------------------------------------------------- sort


def test_sort_context_in_both_directions_leaves_missing_rows_last():
    rows = [
        _transcript(session_id="a", context=9_000),
        _transcript(session_id="b", context=None),
        _transcript(session_id="c", context=120_000),
    ]
    assert _ids(tq.sort_transcripts(rows, "context", ascending=False)) == ["c", "a", "b"]
    assert _ids(tq.sort_transcripts(rows, "context", ascending=True)) == ["a", "c", "b"]


def test_sort_treats_blank_strings_as_missing():
    rows = [
        _transcript(session_id="a", title=""),
        _transcript(session_id="b", title="Zed"),
        _transcript(session_id="c", title="Alpha"),
    ]
    assert _ids(tq.sort_transcripts(rows, "title", ascending=True)) == ["c", "b", "a"]
    assert _ids(tq.sort_transcripts(rows, "title", ascending=False)) == ["b", "c", "a"]


def test_sort_is_stable_for_ties_in_both_directions():
    rows = [_transcript(session_id=str(i), message_count=5) for i in range(4)]
    assert _ids(tq.sort_transcripts(rows, "message_count", ascending=True)) == ["0", "1", "2", "3"]
    assert _ids(tq.sort_transcripts(rows, "message_count", ascending=False)) == ["0", "1", "2", "3"]


def test_sort_by_date_orders_by_time():
    rows = [
        _transcript(session_id="mid", updated_at=datetime(2024, 1, 2)),
        _transcript(session_id="new", updated_at=datetime(2024, 1, 3)),
        _transcript(session_id="none", updated_at=None),
        _transcript(session_id="old", updated_at=datetime(2024, 1, 1)),
    ]
    assert _ids(tq.sort_transcripts(rows, "updated_at", ascending=False)) == ["new", "mid", "old", "none"]


def test_sort_rejects_an_unknown_field():
    with pytest.raises(ValueError):
        tq.sort_transcripts([_transcript()], "path", ascending=True)


# ---------------------------------------------------------------- paging


def test_query_pages_and_reports_the_matching_total():
    rows = [_transcript(session_id=f"s{i:02d}", message_count=i) for i in range(10)]
    first = tq.query(rows, sort="message_count", ascending=True, limit=4, offset=0)
    assert _ids(first.items) == ["s00", "s01", "s02", "s03"]
    assert first.total == 10
    third = tq.query(rows, sort="message_count", ascending=True, limit=4, offset=8)
    assert _ids(third.items) == ["s08", "s09"]


def test_query_total_reflects_filters_and_options_ignore_them():
    rows = [
        _transcript(session_id="a", project="one"),
        _transcript(session_id="b", project="two"),
        _transcript(session_id="c", project="two"),
    ]
    page = tq.query(rows, projects=["two"], limit=1)
    assert page.total == 2
    assert len(page.items) == 1
    assert page.options["projects"] == ["one", "two"]


def test_query_defaults_to_newest_updated_first():
    rows = [
        _transcript(session_id="old", updated_at=datetime(2024, 1, 1)),
        _transcript(session_id="new", updated_at=datetime(2024, 1, 5)),
    ]
    assert _ids(tq.query(rows).items) == ["new", "old"]
