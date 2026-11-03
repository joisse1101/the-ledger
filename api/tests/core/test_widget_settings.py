"""The break length's validator: a whole number of minutes from 1 to 240."""

import pytest

from app.core.widget_settings import DEFAULT_BREAK_MINUTES, validate_break_minutes


def test_the_break_minutes_default_to_sixty():
    assert DEFAULT_BREAK_MINUTES == 60


@pytest.mark.parametrize("value", [1, 45, 60, 240])
def test_a_whole_number_in_range_is_accepted(value):
    assert validate_break_minutes(value) == value


@pytest.mark.parametrize("value", [0, 241, -1])
def test_a_number_out_of_range_is_refused_with_the_range(value):
    with pytest.raises(ValueError, match="from 1 to 240"):
        validate_break_minutes(value)


@pytest.mark.parametrize("value", [7.5, True, "60", None, [60]])
def test_a_value_that_is_not_a_whole_number_is_refused(value):
    with pytest.raises(ValueError, match="whole number"):
        validate_break_minutes(value)
