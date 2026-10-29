"""The desktop widget's display settings: what a stored or submitted value must look like."""

from __future__ import annotations

DEFAULT_MAX_PROJECTS = 5
MIN_MAX_PROJECTS = 1
MAX_MAX_PROJECTS = 10


def validate_max_projects(raw: object) -> int:
    """`raw` as the number of projects the widget lists; ValueError says why not."""
    # A bool is an int in Python, but `true` is not a number of projects.
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError("Enter a whole number.")
    if not MIN_MAX_PROJECTS <= raw <= MAX_MAX_PROJECTS:
        raise ValueError(f"Must be a whole number from {MIN_MAX_PROJECTS} to {MAX_MAX_PROJECTS}.")
    return raw
