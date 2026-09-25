"""Overview-page aggregation: time-range and project filtering, per-group totals, time-of-day activity, summary figures.

Plain Python over `ClaudeTranscript`s - no pandas, no UI - so the API can serve the
numbers and the chart-ready arrays straight to the browser.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Sequence

from claude_transcripts import ClaudeTranscript

# Time-range filter options, in display order:
# - Each value is an inclusive (oldest days ago, newest days ago) pair, e.g.
#   "Past week" = (6, 0) meaning today plus the 6 preceding local dates.
# - "Yesterday" = (1, 1) is the one range that excludes today.
# - "All time" (None) skips filtering entirely.
TIME_RANGES: dict[str, Optional[tuple[int, int]]] = {
    "All time": None,
    "Today": (0, 0),
    "Yesterday": (1, 1),
    "Past week": (6, 0),
    "Past month": (29, 0),
    "Past quarter": (89, 0),
    "Past year": (364, 0),
}

MAX_GROUP_SLICES = 7  # beyond this, fold the tail into "Other"
OTHER = "Other"
NO_BRANCH = "(no branch)"

GROUP_KEYS: dict[str, Callable[[ClaudeTranscript], str]] = {
    "project": lambda transcript: transcript.project,
    "branch": lambda transcript: transcript.git_branch or NO_BRANCH,
}


def filter_by_range(
    transcripts: Sequence[ClaudeTranscript], range_label: str
) -> list[ClaudeTranscript]:
    """Transcripts falling within the chosen time range.

    - Placed by start time, not update time, so a still-running session is
      bucketed by when it began (falls back to last-updated time for the
      rare transcript with no parsed start).
    - Bucketed by local calendar date, not a rolling N*24h window - "Today"
      means today's local date regardless of the current time of day.
    """
    bounds = TIME_RANGES.get(range_label)
    if bounds is None:
        return list(transcripts)
    oldest_days_ago, newest_days_ago = bounds
    today = datetime.now().astimezone().date()
    start_date = today - timedelta(days=oldest_days_ago)
    end_date = today - timedelta(days=newest_days_ago)
    result = []
    for transcript in transcripts:
        anchor = transcript.started_at or transcript.updated_at
        if anchor is None:
            continue
        if start_date <= anchor.astimezone().date() <= end_date:
            result.append(transcript)
    return result


def filter_by_project(
    transcripts: Sequence[ClaudeTranscript], folder: str
) -> list[ClaudeTranscript]:
    """Transcripts filed under one project's on-disk folder.

    Matches the transcript file's parent folder name (`claude_db.sanitize_project_path` of the
    project path), not `transcript.project`, which is only a basename: two projects whose folders
    share a name must not be merged.
    """
    return [t for t in transcripts if t.path.parent.name == folder]


def group_totals(
    transcripts: Sequence[ClaudeTranscript],
    key: Callable[[ClaudeTranscript], str],
    top_n: int = MAX_GROUP_SLICES,
) -> list[dict[str, Any]]:
    """Per-group totals (`key` names a transcript's group), top-N by session count + an "Other" row.

    Every grouped chart shares this split, so a group's color/identity never shifts between
    charts. Each row also carries `share` (% of all sessions) and `messages_pct`/`cost_pct`: that
    measure as a % of the largest row's, so the two measures can share one 0-100 axis instead of a
    dual-axis chart.
    """
    totals: dict[str, dict[str, Any]] = {}
    for transcript in transcripts:
        row = totals.setdefault(
            key(transcript), {"sessions": 0, "messages": 0, "cost": 0.0}
        )
        row["sessions"] += 1
        row["messages"] += transcript.message_count
        row["cost"] += transcript.cost
    if not totals:
        return []

    ranked = sorted(totals.items(), key=lambda item: item[1]["sessions"], reverse=True)
    top, rest = ranked[:top_n], ranked[top_n:]
    rows = [{"group": name, **values} for name, values in top]
    if rest:
        rows.append(
            {
                "group": OTHER,
                "sessions": sum(values["sessions"] for _, values in rest),
                "messages": sum(values["messages"] for _, values in rest),
                "cost": sum(values["cost"] for _, values in rest),
            }
        )

    total_sessions = sum(row["sessions"] for row in rows)
    max_messages = max(row["messages"] for row in rows) or 1
    max_cost = max(row["cost"] for row in rows) or 1
    for row in rows:
        row["share"] = 100 * row["sessions"] / total_sessions
        row["messages_pct"] = 100 * row["messages"] / max_messages
        row["cost_pct"] = 100 * row["cost"] / max_cost
    return rows


BUCKET_MINUTES = 30
BUCKET_SIZES = (30, 60)


def format_bucket(minute: int) -> str:
    """Clock label for a bucket's start, `minute` minutes after local midnight: `9:30am`."""
    hour, mins = divmod(minute, 60)
    period = "am" if hour < 12 else "pm"
    return f"{hour % 12 or 12}:{mins:02d}{period}"


def time_of_day_activity(
    transcripts: Sequence[ClaudeTranscript], bucket_minutes: int = BUCKET_MINUTES
) -> list[dict[str, Any]]:
    """Session/message counts per local block of the day (`bucket_minutes` long, one of
    `BUCKET_SIZES`), trimmed to the span with activity.

    A session counts in the block its start time falls in. Blocks between the first and last
    active one are zero-filled; with no activity at all, every block of the day is returned.
    Each row's `minute` is the block's start, in minutes after midnight.
    """
    buckets_per_day = 24 * 60 // bucket_minutes
    sessions = [0] * buckets_per_day
    messages = [0] * buckets_per_day
    for transcript in transcripts:
        anchor = transcript.started_at or transcript.updated_at
        if anchor is None:
            continue
        local = anchor.astimezone()
        bucket = (local.hour * 60 + local.minute) // bucket_minutes
        sessions[bucket] += 1
        messages[bucket] += transcript.message_count

    active = [bucket for bucket, count in enumerate(sessions) if count > 0]
    first, last = (min(active), max(active)) if active else (0, buckets_per_day - 1)
    return [
        {
            "minute": bucket * bucket_minutes,
            "label": format_bucket(bucket * bucket_minutes),
            "sessions": sessions[bucket],
            "messages": messages[bucket],
        }
        for bucket in range(first, last + 1)
    ]


def format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "—"
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def _duration(seconds: float) -> dict[str, Any]:
    return {"seconds": seconds, "label": format_duration(seconds)}


def _money(amount: float) -> dict[str, Any]:
    return {"amount": amount, "label": f"${amount:,.2f}"}


def _with_session(
    figure: dict[str, Any], transcript: Optional[ClaudeTranscript]
) -> dict[str, Any]:
    """Attach which project/session an extreme value belongs to."""
    figure["project"] = transcript.project if transcript else None
    figure["session_id"] = transcript.session_id if transcript else None
    return figure


def summary(transcripts: Sequence[ClaudeTranscript]) -> dict[str, Any]:
    """The KPI figures: counts, session durations, session costs (extremes name their session)."""
    num_sessions = len(transcripts)
    total_messages = sum(t.message_count for t in transcripts)

    durations = [
        ((t.updated_at - t.started_at).total_seconds(), t)
        for t in transcripts
        if t.started_at and t.updated_at
    ]
    total_duration = sum(seconds for seconds, _ in durations)
    longest = max(durations, key=lambda entry: entry[0]) if durations else None
    shortest = min(durations, key=lambda entry: entry[0]) if durations else None

    total_cost = sum(t.cost for t in transcripts)
    most_expensive = max(transcripts, key=lambda t: t.cost) if transcripts else None
    cheapest = min(transcripts, key=lambda t: t.cost) if transcripts else None

    return {
        "projects": len({t.project for t in transcripts}),
        "sessions": num_sessions,
        "messages": total_messages,
        "avg_messages_per_session": total_messages / num_sessions if num_sessions else None,
        "duration": {
            "average": _duration(total_duration / len(durations) if durations else 0),
            "longest": _with_session(
                _duration(longest[0] if longest else 0), longest[1] if longest else None
            ),
            "shortest": _with_session(
                _duration(shortest[0] if shortest else 0), shortest[1] if shortest else None
            ),
            "total": _duration(total_duration),
        },
        "cost": {
            "average": _money(total_cost / num_sessions if num_sessions else 0),
            "most_expensive": _with_session(
                _money(most_expensive.cost if most_expensive else 0), most_expensive
            ),
            "cheapest": _with_session(
                _money(cheapest.cost if cheapest else 0), cheapest
            ),
            "total": _money(total_cost),
        },
    }


def overview(
    transcripts: Sequence[ClaudeTranscript],
    range_label: str,
    project_folder: Optional[str] = None,
    group_by: str = "project",
    bucket_minutes: int = BUCKET_MINUTES,
) -> dict[str, Any]:
    """Everything the Overview page (or one project's panel) shows for one time range.

    `project_folder`, when given, limits it to that project's transcripts (see
    `filter_by_project`). `group_by` (`GROUP_KEYS`) picks what the donut/bar rows are grouped by.
    `group_order` is the one ordering every grouped chart uses (colors follow a group's index in
    it; "Other", when present, is last). `bucket_minutes` (`BUCKET_SIZES`) sets the block size of
    the time-of-day `activity`.
    """
    if project_folder is not None:
        transcripts = filter_by_project(transcripts, project_folder)
    filtered = filter_by_range(transcripts, range_label)
    if not filtered:
        return {"range": range_label, "empty": True}
    groups = group_totals(filtered, GROUP_KEYS[group_by])
    return {
        "range": range_label,
        "empty": False,
        "summary": summary(filtered),
        "groups": groups,
        "group_order": [row["group"] for row in groups],
        "activity": time_of_day_activity(filtered, bucket_minutes),
    }
