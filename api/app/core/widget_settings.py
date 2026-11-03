"""The desktop widget's display settings: what a stored or submitted value must look like."""

from __future__ import annotations

DEFAULT_MAX_PROJECTS = 5
MIN_MAX_PROJECTS = 1
MAX_MAX_PROJECTS = 10

DEFAULT_AFK_MINUTES = 30
MIN_AFK_MINUTES = 1
MAX_AFK_MINUTES = 240

DEFAULT_BREAK_MINUTES = 60
MIN_BREAK_MINUTES = 1
MAX_BREAK_MINUTES = 240


def validate_max_projects(raw: object) -> int:
    """`raw` as the number of projects the widget lists; ValueError says why not."""
    # A bool is an int in Python, but `true` is not a number of projects.
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError("Enter a whole number.")
    if not MIN_MAX_PROJECTS <= raw <= MAX_MAX_PROJECTS:
        raise ValueError(f"Must be a whole number from {MIN_MAX_PROJECTS} to {MAX_MAX_PROJECTS}.")
    return raw


def validate_afk_minutes(raw: object) -> int:
    """`raw` as the minutes the widget's AFK switch stays on; ValueError says why not."""
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError("Enter a whole number.")
    if not MIN_AFK_MINUTES <= raw <= MAX_AFK_MINUTES:
        raise ValueError(f"Must be a whole number from {MIN_AFK_MINUTES} to {MAX_AFK_MINUTES}.")
    return raw


def validate_break_minutes(raw: object) -> int:
    """`raw` as the minutes of work before the widget's break window opens; ValueError says why not."""
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError("Enter a whole number.")
    if not MIN_BREAK_MINUTES <= raw <= MAX_BREAK_MINUTES:
        raise ValueError(f"Must be a whole number from {MIN_BREAK_MINUTES} to {MAX_BREAK_MINUTES}.")
    return raw
