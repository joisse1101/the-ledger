from datetime import datetime, timedelta, timezone

import pytest

from app.domain.compact_grade import grade_compact

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


def _ago(**delta):
    return NOW - timedelta(**delta)


@pytest.mark.parametrize(
    "age, state",
    [
        (timedelta(minutes=20), "ok"),
        (timedelta(minutes=44, seconds=59), "ok"),
        (timedelta(minutes=45), "should"),
        (timedelta(minutes=55), "should"),
        (timedelta(minutes=55, seconds=1), "needs"),
        (timedelta(hours=3), "needs"),
    ],
)
def test_bands_from_the_start(age, state):
    assert grade_compact(NOW - age, None, NOW).state == state


def test_a_recent_compaction_restarts_the_clock():
    grade = grade_compact(_ago(hours=3), _ago(minutes=10), NOW)
    assert grade.state == "ok"
    assert grade.since == _ago(minutes=10)


def test_only_the_latest_compaction_counts():
    assert grade_compact(_ago(hours=3), _ago(minutes=50), NOW).state == "should"


def test_a_compaction_older_than_the_start_is_ignored():
    grade = grade_compact(_ago(minutes=10), _ago(hours=2), NOW)
    assert grade.state == "ok"
    assert grade.since == _ago(minutes=10)


def test_a_naive_start_is_read_as_local_time():
    local_start = (NOW - timedelta(minutes=50)).astimezone().replace(tzinfo=None)
    grade = grade_compact(local_start, None, NOW)
    assert grade.state == "should"
    assert grade.since == _ago(minutes=50)


def test_no_start_and_no_compaction_has_no_grade():
    assert grade_compact(None, None, NOW) is None


def test_a_compaction_alone_is_enough():
    assert grade_compact(None, _ago(minutes=60), NOW).state == "needs"
