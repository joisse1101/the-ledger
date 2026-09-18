from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

import views.overview as overview
from claude_transcripts import ClaudeTranscript

_FROZEN_NOW = datetime(2024, 6, 15, 12, 0, 0)


class _FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return _FROZEN_NOW if tz is None else _FROZEN_NOW.astimezone(tz)


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch):
    monkeypatch.setattr(overview, "datetime", _FrozenDateTime)


def _transcript(started_at=None, updated_at=None, message_count=0, cost=0.0, project="proj"):
    return ClaudeTranscript(
        session_id="s",
        path=Path("x.jsonl"),
        cwd="/x",
        version="1.0",
        git_branch="main",
        started_at=started_at,
        updated_at=updated_at,
        message_count=message_count,
        cost=cost,
        project=project,
    )


# ---------------------------------------------------------------------------
# _filter_transcripts_by_range
# ---------------------------------------------------------------------------


def test_filter_all_time_returns_everything():
    transcripts = [_transcript(started_at=datetime(2020, 1, 1))]
    result = overview._filter_transcripts_by_range(transcripts, "All time")
    assert result == transcripts


def test_filter_today_includes_only_todays_local_date():
    today_t = _transcript(started_at=datetime(2024, 6, 15, 9, 0, 0))
    yesterday_t = _transcript(started_at=datetime(2024, 6, 14, 23, 59, 0))
    result = overview._filter_transcripts_by_range([today_t, yesterday_t], "Today")
    assert result == [today_t]


def test_filter_yesterday_excludes_today():
    today_t = _transcript(started_at=datetime(2024, 6, 15, 0, 1, 0))
    yesterday_t = _transcript(started_at=datetime(2024, 6, 14, 12, 0, 0))
    result = overview._filter_transcripts_by_range([today_t, yesterday_t], "Yesterday")
    assert result == [yesterday_t]


def test_filter_past_week_is_seven_calendar_days_inclusive():
    in_range = _transcript(started_at=datetime(2024, 6, 9, 0, 0, 0))  # 6 days ago
    out_of_range = _transcript(started_at=datetime(2024, 6, 8, 23, 59, 0))  # 7 days ago
    result = overview._filter_transcripts_by_range([in_range, out_of_range], "Past week")
    assert result == [in_range]


def test_filter_falls_back_to_updated_at_when_no_started_at():
    t = _transcript(started_at=None, updated_at=datetime(2024, 6, 15, 9, 0, 0))
    result = overview._filter_transcripts_by_range([t], "Today")
    assert result == [t]


def test_filter_skips_transcript_with_no_timestamps():
    t = _transcript(started_at=None, updated_at=None)
    result = overview._filter_transcripts_by_range([t], "Today")
    assert result == []


# ---------------------------------------------------------------------------
# _project_totals_dataframe
# ---------------------------------------------------------------------------


def test_project_totals_empty_returns_empty_dataframe():
    df = overview._project_totals_dataframe([])
    assert list(df.columns) == ["Project", "Sessions", "Messages", "Cost", "Percent"]
    assert df.empty


def test_project_totals_aggregates_per_project():
    transcripts = [
        _transcript(project="a", message_count=10, cost=1.0),
        _transcript(project="a", message_count=5, cost=0.5),
        _transcript(project="b", message_count=3, cost=0.25),
    ]
    df = overview._project_totals_dataframe(transcripts).set_index("Project")
    assert df.loc["a", "Sessions"] == 2
    assert df.loc["a", "Messages"] == 15
    assert df.loc["a", "Cost"] == pytest.approx(1.5)
    assert df.loc["b", "Sessions"] == 1


def test_project_totals_folds_tail_into_other_ranked_by_sessions():
    # 3 sessions for "a", 2 for "b", 1 each for c/d/e -> top_n=2 keeps a, b.
    transcripts = (
        [_transcript(project="a")] * 3
        + [_transcript(project="b")] * 2
        + [_transcript(project="c")]
        + [_transcript(project="d")]
        + [_transcript(project="e")]
    )
    df = overview._project_totals_dataframe(transcripts, top_n=2)
    assert list(df["Project"]) == ["a", "b", "Other"]
    other = df[df["Project"] == "Other"].iloc[0]
    assert other["Sessions"] == 3  # c + d + e


def test_project_totals_percent_sums_to_100():
    transcripts = [_transcript(project="a")] * 3 + [_transcript(project="b")]
    df = overview._project_totals_dataframe(transcripts)
    assert df[df["Project"] == "a"].iloc[0]["Percent"] == "75.0%"
    assert df[df["Project"] == "b"].iloc[0]["Percent"] == "25.0%"


# ---------------------------------------------------------------------------
# _hourly_activity_dataframe
# ---------------------------------------------------------------------------


def test_hourly_activity_zero_fills_all_24_hours():
    df = overview._hourly_activity_dataframe([])
    assert len(df) == 24
    assert df["Sessions"].sum() == 0
    assert df["Messages"].sum() == 0


def test_hourly_activity_buckets_by_local_start_hour():
    transcripts = [
        _transcript(started_at=datetime(2024, 6, 15, 9, 30, 0), message_count=4),
        _transcript(started_at=datetime(2024, 6, 15, 9, 45, 0), message_count=6),
        _transcript(started_at=datetime(2024, 6, 15, 14, 0, 0), message_count=2),
    ]
    df = overview._hourly_activity_dataframe(transcripts)
    nine_am = df[df["Label"] == "9am"].iloc[0]
    assert nine_am["Sessions"] == 2
    assert nine_am["Messages"] == 10
    two_pm = df[df["Label"] == "2pm"].iloc[0]
    assert two_pm["Sessions"] == 1


def test_hourly_activity_trims_to_hours_with_activity():
    transcripts = [
        _transcript(started_at=datetime(2024, 6, 15, 9, 30, 0)),
        _transcript(started_at=datetime(2024, 6, 15, 14, 0, 0)),
    ]
    df = overview._hourly_activity_dataframe(transcripts)
    assert list(df["Label"]) == [overview._format_hour(h) for h in range(9, 15)]


def test_hourly_activity_skips_transcript_with_no_timestamps():
    t = _transcript(started_at=None, updated_at=None)
    df = overview._hourly_activity_dataframe([t])
    assert df["Sessions"].sum() == 0


# ---------------------------------------------------------------------------
# _format_duration / _format_hour
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, "—"),
        (-5, "—"),
        (45, "45s"),
        (125, "2m 5s"),
        (3665, "1h 1m"),
    ],
)
def test_format_duration(seconds, expected):
    assert overview._format_duration(seconds) == expected


@pytest.mark.parametrize(
    "hour,expected",
    [
        (0, "12am"),
        (9, "9am"),
        (12, "12pm"),
        (13, "1pm"),
        (23, "11pm"),
    ],
)
def test_format_hour(hour, expected):
    assert overview._format_hour(hour) == expected


# ---------------------------------------------------------------------------
# _project_color_scale
# ---------------------------------------------------------------------------


def test_project_color_scale_without_other():
    df = pd.DataFrame({"Project": ["a", "b"]})
    domain, color_range = overview._project_color_scale(df, ["h0", "h1", "h2"])
    assert domain == ["a", "b"]
    assert color_range == ["h0", "h1"]


def test_project_color_scale_with_other_uses_muted_ink():
    df = pd.DataFrame({"Project": ["a", "b", "Other"]})
    domain, color_range = overview._project_color_scale(df, ["h0", "h1", "h2"])
    assert domain == ["a", "b", "Other"]
    assert color_range == ["h0", "h1", overview._MUTED_INK]
