from datetime import datetime
from pathlib import Path

import pytest

import overview_stats as overview
from claude_transcripts import ClaudeTranscript

_FROZEN_NOW = datetime(2024, 6, 15, 12, 0, 0)


class _FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return _FROZEN_NOW if tz is None else _FROZEN_NOW.astimezone(tz)


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch):
    monkeypatch.setattr(overview, "datetime", _FrozenDateTime)


def _transcript(
    started_at=None, updated_at=None, message_count=0, cost=0.0, project="proj", session_id="s"
):
    return ClaudeTranscript(
        session_id=session_id,
        path=Path("x.jsonl"),
        cwd="/x",
        version="1.0",
        git_branch="main",
        started_at=started_at,
        updated_at=updated_at,
        message_count=message_count,
        cost=cost,
        project=project,
        title="",
        last_message="",
        first_prompt="",
    )


# ---------------------------------------------------------------------------
# filter_by_range
# ---------------------------------------------------------------------------


def test_filter_all_time_returns_everything():
    transcripts = [_transcript(started_at=datetime(2020, 1, 1))]
    assert overview.filter_by_range(transcripts, "All time") == transcripts


def test_filter_today_includes_only_todays_local_date():
    today_t = _transcript(started_at=datetime(2024, 6, 15, 9, 0, 0))
    yesterday_t = _transcript(started_at=datetime(2024, 6, 14, 23, 59, 0))
    assert overview.filter_by_range([today_t, yesterday_t], "Today") == [today_t]


def test_filter_yesterday_excludes_today():
    today_t = _transcript(started_at=datetime(2024, 6, 15, 0, 1, 0))
    yesterday_t = _transcript(started_at=datetime(2024, 6, 14, 12, 0, 0))
    assert overview.filter_by_range([today_t, yesterday_t], "Yesterday") == [yesterday_t]


def test_filter_past_week_is_seven_calendar_days_inclusive():
    in_range = _transcript(started_at=datetime(2024, 6, 9, 0, 0, 0))  # 6 days ago
    out_of_range = _transcript(started_at=datetime(2024, 6, 8, 23, 59, 0))  # 7 days ago
    assert overview.filter_by_range([in_range, out_of_range], "Past week") == [in_range]


def test_filter_falls_back_to_updated_at_when_no_started_at():
    t = _transcript(started_at=None, updated_at=datetime(2024, 6, 15, 9, 0, 0))
    assert overview.filter_by_range([t], "Today") == [t]


def test_filter_skips_transcript_with_no_timestamps():
    t = _transcript(started_at=None, updated_at=None)
    assert overview.filter_by_range([t], "Today") == []


# ---------------------------------------------------------------------------
# project_totals
# ---------------------------------------------------------------------------


def test_project_totals_empty_returns_empty_list():
    assert overview.project_totals([]) == []


def test_project_totals_aggregates_per_project():
    transcripts = [
        _transcript(project="a", message_count=10, cost=1.0),
        _transcript(project="a", message_count=5, cost=0.5),
        _transcript(project="b", message_count=3, cost=0.25),
    ]
    rows = {row["project"]: row for row in overview.project_totals(transcripts)}
    assert rows["a"]["sessions"] == 2
    assert rows["a"]["messages"] == 15
    assert rows["a"]["cost"] == pytest.approx(1.5)
    assert rows["b"]["sessions"] == 1


def test_project_totals_folds_tail_into_other_ranked_by_sessions():
    # 3 sessions for "a", 2 for "b", 1 each for c/d/e -> top_n=2 keeps a, b.
    transcripts = (
        [_transcript(project="a")] * 3
        + [_transcript(project="b")] * 2
        + [_transcript(project="c")]
        + [_transcript(project="d")]
        + [_transcript(project="e")]
    )
    rows = overview.project_totals(transcripts, top_n=2)
    assert [row["project"] for row in rows] == ["a", "b", "Other"]
    assert rows[2]["sessions"] == 3  # c + d + e


def test_project_totals_with_ten_projects_shows_seven_plus_other():
    # Projects p0..p9 with 10, 9, ... 1 sessions: the seven busiest stay, p7..p9 fold.
    transcripts = [
        _transcript(project=f"p{i}", message_count=1, cost=1.0)
        for i in range(10)
        for _ in range(10 - i)
    ]
    rows = overview.project_totals(transcripts)
    assert [row["project"] for row in rows] == [f"p{i}" for i in range(7)] + ["Other"]
    assert rows[-1]["sessions"] == 3 + 2 + 1
    assert rows[-1]["messages"] == 6


def test_project_totals_share_sums_to_100():
    transcripts = [_transcript(project="a")] * 3 + [_transcript(project="b")]
    rows = {row["project"]: row for row in overview.project_totals(transcripts)}
    assert rows["a"]["share"] == pytest.approx(75.0)
    assert rows["b"]["share"] == pytest.approx(25.0)


def test_project_totals_normalizes_each_measure_to_its_own_peak():
    transcripts = [
        _transcript(project="a", message_count=100, cost=1.0),
        _transcript(project="b", message_count=50, cost=4.0),
    ]
    rows = {row["project"]: row for row in overview.project_totals(transcripts)}
    assert rows["a"]["messages_pct"] == pytest.approx(100.0)
    assert rows["b"]["messages_pct"] == pytest.approx(50.0)
    assert rows["a"]["cost_pct"] == pytest.approx(25.0)
    assert rows["b"]["cost_pct"] == pytest.approx(100.0)


def test_project_totals_with_all_zero_measures_does_not_divide_by_zero():
    rows = overview.project_totals([_transcript(project="a")])
    assert rows[0]["messages_pct"] == 0
    assert rows[0]["cost_pct"] == 0


# ---------------------------------------------------------------------------
# hourly_activity
# ---------------------------------------------------------------------------


def test_hourly_activity_with_no_transcripts_zero_fills_all_24_hours():
    rows = overview.hourly_activity([])
    assert len(rows) == 24
    assert sum(row["sessions"] for row in rows) == 0
    assert sum(row["messages"] for row in rows) == 0


def test_hourly_activity_buckets_by_local_start_hour():
    transcripts = [
        _transcript(started_at=datetime(2024, 6, 15, 9, 30, 0), message_count=4),
        _transcript(started_at=datetime(2024, 6, 15, 9, 45, 0), message_count=6),
        _transcript(started_at=datetime(2024, 6, 15, 14, 0, 0), message_count=2),
    ]
    rows = {row["label"]: row for row in overview.hourly_activity(transcripts)}
    assert rows["9am"]["sessions"] == 2
    assert rows["9am"]["messages"] == 10
    assert rows["2pm"]["sessions"] == 1


def test_hourly_activity_trims_to_hours_with_activity():
    transcripts = [
        _transcript(started_at=datetime(2024, 6, 15, 9, 30, 0)),
        _transcript(started_at=datetime(2024, 6, 15, 14, 0, 0)),
    ]
    rows = overview.hourly_activity(transcripts)
    assert [row["label"] for row in rows] == [overview.format_hour(h) for h in range(9, 15)]


def test_hourly_activity_normalizes_each_measure_to_its_busiest_hour():
    transcripts = [
        _transcript(started_at=datetime(2024, 6, 15, 9, 0, 0), message_count=10),
        _transcript(started_at=datetime(2024, 6, 15, 9, 5, 0), message_count=10),
        _transcript(started_at=datetime(2024, 6, 15, 10, 0, 0), message_count=40),
    ]
    rows = {row["label"]: row for row in overview.hourly_activity(transcripts)}
    assert rows["9am"]["sessions_pct"] == pytest.approx(100.0)
    assert rows["10am"]["sessions_pct"] == pytest.approx(50.0)
    assert rows["9am"]["messages_pct"] == pytest.approx(50.0)
    assert rows["10am"]["messages_pct"] == pytest.approx(100.0)


def test_hourly_activity_skips_transcript_with_no_timestamps():
    t = _transcript(started_at=None, updated_at=None)
    assert sum(row["sessions"] for row in overview.hourly_activity([t])) == 0


# ---------------------------------------------------------------------------
# format_duration / format_hour
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "seconds,expected",
    [(0, "—"), (-5, "—"), (45, "45s"), (125, "2m 5s"), (3665, "1h 1m")],
)
def test_format_duration(seconds, expected):
    assert overview.format_duration(seconds) == expected


@pytest.mark.parametrize(
    "hour,expected",
    [(0, "12am"), (9, "9am"), (12, "12pm"), (13, "1pm"), (23, "11pm")],
)
def test_format_hour(hour, expected):
    assert overview.format_hour(hour) == expected


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------


def test_summary_counts_and_names_the_extreme_sessions():
    transcripts = [
        _transcript(
            project="a", session_id="quick", message_count=4, cost=0.5,
            started_at=datetime(2024, 6, 15, 9, 0, 0), updated_at=datetime(2024, 6, 15, 9, 0, 30),
        ),
        _transcript(
            project="b", session_id="slow", message_count=6, cost=2.0,
            started_at=datetime(2024, 6, 15, 10, 0, 0), updated_at=datetime(2024, 6, 15, 11, 1, 0),
        ),
    ]
    result = overview.summary(transcripts)
    assert result["projects"] == 2
    assert result["sessions"] == 2
    assert result["messages"] == 10
    assert result["avg_messages_per_session"] == pytest.approx(5.0)
    assert result["duration"]["longest"]["label"] == "1h 1m"
    assert (result["duration"]["longest"]["project"], result["duration"]["longest"]["session_id"]) == ("b", "slow")
    assert result["duration"]["shortest"]["session_id"] == "quick"
    assert result["cost"]["most_expensive"]["label"] == "$2.00"
    assert result["cost"]["most_expensive"]["session_id"] == "slow"
    assert result["cost"]["cheapest"]["session_id"] == "quick"
    assert result["cost"]["total"]["label"] == "$2.50"
    assert result["cost"]["average"]["label"] == "$1.25"


def test_summary_of_nothing_is_placeholders_not_errors():
    result = overview.summary([])
    assert result["sessions"] == 0
    assert result["avg_messages_per_session"] is None
    assert result["duration"]["longest"]["label"] == "—"
    assert result["duration"]["longest"]["session_id"] is None
    assert result["cost"]["most_expensive"]["label"] == "$0.00"


# ---------------------------------------------------------------------------
# overview
# ---------------------------------------------------------------------------


def test_overview_for_an_empty_range_is_an_empty_state_not_an_error():
    old = _transcript(started_at=datetime(2020, 1, 1))
    assert overview.overview([old], "Yesterday") == {"range": "Yesterday", "empty": True}


def test_overview_project_order_matches_project_rows():
    transcripts = [_transcript(project="a")] * 2 + [_transcript(project="b")]
    result = overview.overview(transcripts, "All time")
    assert result["empty"] is False
    assert result["project_order"] == [row["project"] for row in result["projects"]] == ["a", "b"]
