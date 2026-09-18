from datetime import datetime, timedelta

from app import _AUTO_REFRESH_INTERVAL, _auto_refresh_due

_NOW = datetime(2024, 6, 15, 12, 0, 0)


def test_not_due_on_first_ever_call():
    # last is None - main() already seeds the snapshot before this fires,
    # so there's nothing to redo yet.
    assert _auto_refresh_due(None, _NOW) is False


def test_not_due_before_interval_elapses():
    last = _NOW - (_AUTO_REFRESH_INTERVAL - timedelta(seconds=1))
    assert _auto_refresh_due(last, _NOW) is False


def test_due_once_interval_elapses():
    last = _NOW - _AUTO_REFRESH_INTERVAL
    assert _auto_refresh_due(last, _NOW) is True


def test_due_after_interval_elapses():
    last = _NOW - _AUTO_REFRESH_INTERVAL - timedelta(minutes=5)
    assert _auto_refresh_due(last, _NOW) is True
