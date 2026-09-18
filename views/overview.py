from datetime import datetime, timedelta
from typing import Optional, Sequence

import pandas as pd
import streamlit as st
from streamlit import config as st_config

from claude_transcripts import ClaudeTranscript, load_transcripts

# Time-range filter options, in display order:
# - Each value is an inclusive (oldest days ago, newest days ago) pair, e.g.
#   "Past week" = (6, 0) meaning today plus the 6 preceding local dates.
# - "Yesterday" = (1, 1) is the one range that excludes today.
# - "All time" (None) skips filtering entirely.
_TIME_RANGES: dict[str, Optional[tuple[int, int]]] = {
    "All time": None,
    "Today": (0, 0),
    "Yesterday": (1, 1),
    "Past week": (6, 0),
    "Past month": (29, 0),
    "Past quarter": (89, 0),
    "Past year": (364, 0),
}

# Fixed-order categorical palette (Harmonized Pastel & Rose Theme)
# Slots are strictly aligned so a given index always maps to the same hue family across themes.
# Validated against the dataviz skill's scripts/validate_palette.js (lightness band,
# chroma floor, CVD separation, normal-vision floor, contrast vs surface) for both
# modes - re-run it against any future edit here rather than eyeballing a swap.
_CATEGORICAL_LIGHT = [
    "#d6487e",  # 0: Brand Rose Anchor     (Fixed, matches Dark Rose)
    "#0891b2",  # 1: Deep Cyan-Teal        (Matches Dark Teal; re-hued off rose to clear CVD)
    "#d97706",  # 2: Soft Amber / Gold     (Matches Dark Sun Gold)
    "#059669",  # 3: Soft Emerald          (Matches Dark Mint; moved off Lime to clear CVD)
    "#3b82f6",  # 4: Soft Periwinkle Blue  (Matches Dark Sky Blue)
    "#e06d53",  # 5: Pastel Coral / Orange (Matches Dark Peach-Orange)
    "#a259ff",  # 6: Pastel Purple         (Matches Dark Lilac)
    "#65a30d",  # 7: Leaf Green / Lime     (Matches Dark Lime)
]

_CATEGORICAL_DARK = [
    "#c26d88",  # 0: Brand Rose Anchor     (Fixed, matches Light Rose)
    "#0099ca",  # 1: Vibrant Cyan-Teal     (Matches Light Teal)
    "#c87b00",  # 2: Soft Sun Gold         (Matches Light Amber)
    "#009362",  # 3: Bright Soft Mint      (Matches Light Emerald)
    "#0094da",  # 4: Electric Sky Blue     (Matches Light Blue)
    "#e65f2a",  # 5: Pastel Peach-Orange   (Matches Light Coral)
    "#a260df",  # 6: Pastel Lilac / Orchid (Matches Light Purple)
    "#5a9400",  # 7: Bright Lime/Chartreuse(Matches Light Leaf Green)
]
_MUTED_INK = "#898781"  # "Other" bucket - same in both modes
_MAX_PROJECT_SLICES = 7  # beyond this, fold the tail into "Other"


def _filter_transcripts_by_range(
    transcripts: Sequence[ClaudeTranscript], range_label: str
) -> Sequence[ClaudeTranscript]:
    """Transcripts falling within the chosen time range.

    - Placed by start time, not update time, so a still-running session is
      bucketed by when it began (falls back to last-updated time for the
      rare transcript with no parsed start).
    """
    bounds = _TIME_RANGES.get(range_label)
    if bounds is None:
        return transcripts
    oldest_days_ago, newest_days_ago = bounds
    # Bucketed by local calendar date, not a rolling N*24h window - "Today"
    # means today's local date regardless of the current time of day.
    today = datetime.now().astimezone().date()
    start_date = today - timedelta(days=oldest_days_ago)
    end_date = today - timedelta(days=newest_days_ago)
    result = []
    for transcript in transcripts:
        anchor = transcript.started_at or transcript.updated_at
        if anchor is None:
            continue
        anchor_date = anchor.astimezone().date()
        if start_date <= anchor_date <= end_date:
            result.append(transcript)
    return result


def _project_totals_dataframe(
    transcripts: Sequence[ClaudeTranscript], top_n: int = _MAX_PROJECT_SLICES
) -> pd.DataFrame:
    """Per-project totals, top-N by session count + an "Other" row for the rest.

    - Every project chart on this page shares this same split, so a project's
      color/identity never shifts between charts.
    """
    totals: dict[str, dict] = {}
    for transcript in transcripts:
        row = totals.setdefault(
            transcript.project, {"Sessions": 0, "Messages": 0, "Cost": 0.0}
        )
        row["Sessions"] += 1
        row["Messages"] += transcript.message_count
        row["Cost"] += transcript.cost
    if not totals:
        return pd.DataFrame(
            columns=["Project", "Sessions", "Messages", "Cost", "Percent"]
        )

    ranked = sorted(totals.items(), key=lambda item: item[1]["Sessions"], reverse=True)
    top_projects, rest = ranked[:top_n], ranked[top_n:]
    rows = [{"Project": name, **values} for name, values in top_projects]
    if rest:
        rows.append(
            {
                "Project": "Other",
                "Sessions": sum(values["Sessions"] for _, values in rest),
                "Messages": sum(values["Messages"] for _, values in rest),
                "Cost": sum(values["Cost"] for _, values in rest),
            }
        )

    total_sessions = sum(row["Sessions"] for row in rows)
    for row in rows:
        row["Percent"] = f"{100 * row['Sessions'] / total_sessions:.1f}%"
    return pd.DataFrame(rows)


def _theme_colors() -> tuple[bool, list[str], str, str, str, str]:
    """(is_dark, categorical hues, surface, text-primary, text-secondary, grid)."""
    is_dark = st_config.get_option("theme.base") == "dark"
    hues = _CATEGORICAL_DARK if is_dark else _CATEGORICAL_LIGHT
    surface = "#1a1a19" if is_dark else "#fcfcfb"
    text_primary = "#ffffff" if is_dark else "#0b0b0b"
    text_secondary = "#c3c2b7" if is_dark else "#52514e"
    grid = "#2b2a27" if is_dark else "#e8e7e1"
    return is_dark, hues, surface, text_primary, text_secondary, grid


def _project_color_scale(
    df: pd.DataFrame, hues: Sequence[str]
) -> tuple[list[str], list[str]]:
    """Domain/range for a Project color encoding, shared across charts so a project keeps its hue."""
    domain = list(df["Project"])
    has_other = "Other" in domain
    named_count = len(domain) - (1 if has_other else 0)
    color_range = list(hues[:named_count]) + ([_MUTED_INK] if has_other else [])
    return domain, color_range


def _format_hour(hour: int) -> str:
    period = "am" if hour < 12 else "pm"
    display = hour % 12 or 12
    return f"{display}{period}"


def _hourly_activity_dataframe(transcripts: Sequence[ClaudeTranscript]) -> pd.DataFrame:
    """Session/message counts per local hour of day, trimmed to the hours with any activity."""

    sessions = [0] * 24
    messages = [0] * 24
    for transcript in transcripts:
        anchor = transcript.started_at or transcript.updated_at
        if anchor is None:
            continue
        hour = anchor.astimezone().hour
        sessions[hour] += 1
        messages[hour] += transcript.message_count

    min_hour = (
        min(hour for hour, count in enumerate(sessions) if count > 0)
        if any(sessions)
        else 0
    )
    max_hour = (
        max(hour for hour, count in enumerate(sessions) if count > 0)
        if any(sessions)
        else 23
    )
    return pd.DataFrame(
        {
            "Label": [_format_hour(hour) for hour in range(min_hour, max_hour + 1)],
            "Sessions": sessions[min_hour : max_hour + 1],
            "Messages": messages[min_hour : max_hour + 1],
        }
    )


def _format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "—"
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def _render_summary_stats(transcripts: Sequence[ClaudeTranscript]) -> None:
    num_projects = len({transcript.project for transcript in transcripts})
    num_sessions = len(transcripts)
    total_messages = sum(transcript.message_count for transcript in transcripts)

    durations = [
        ((transcript.updated_at - transcript.started_at).total_seconds(), transcript)
        for transcript in transcripts
        if transcript.started_at and transcript.updated_at
    ]

    costs = [(transcript.cost, transcript) for transcript in transcripts]

    total = sum(duration for duration, _ in durations)
    avg_seconds = total / len(durations) if durations else 0
    longest = max(durations, key=lambda entry: entry[0]) if durations else None
    shortest = min(durations, key=lambda entry: entry[0]) if durations else None

    total_cost = sum(cost for cost, _ in costs)
    most_expensive = max(costs, key=lambda entry: entry[0])[1] if costs else None
    avg_cost = total_cost / len(costs) if costs else 0
    cheapest = min(costs, key=lambda entry: entry[0])[1] if costs else None

    def _session_help(entry: tuple[float, ClaudeTranscript] | None) -> str | None:
        """Metric tooltip text naming which project/session an extreme value belongs to."""
        if entry is None:
            return None
        _, transcript = entry
        # A trailing two-space hard break, since st.metric's help text renders
        # as markdown and a bare "\n" gets collapsed.
        return f"{transcript.project}  \n{transcript.session_id}"

    col_one, col_two, col_three = st.columns(3)
    with col_one:
        st.metric("Projects", num_projects)
        st.metric("Sessions", num_sessions)
        st.metric("Messages", f"{total_messages:,}")
        st.metric(
            "Avg. messages per session",
            f"{total_messages / num_sessions:.1f}" if num_sessions else "—",
        )
    with col_two:
        st.metric("Avg. session", _format_duration(avg_seconds))
        st.metric(
            "Longest session",
            _format_duration(longest[0]) if longest else _format_duration(0),
            help=_session_help(longest),
        )
        st.metric(
            "Shortest session",
            _format_duration(shortest[0]) if shortest else _format_duration(0),
            help=_session_help(shortest),
        )
        st.metric("Total", _format_duration(total))
    with col_three:
        st.metric("Avg. session cost", f"${avg_cost:,.2f}")
        st.metric(
            "Most expensive session",
            f"${most_expensive.cost:,.2f}" if most_expensive else "$0.00",
            help=_session_help(
                (most_expensive.cost, most_expensive) if most_expensive else None
            ),
        )
        st.metric(
            "Cheapest session",
            f"${cheapest.cost:,.2f}" if cheapest else "$0.00",
            help=_session_help((cheapest.cost, cheapest) if cheapest else None),
        )
        st.metric("Est. total cost", f"${total_cost:,.2f}")


def _render_project_sessions_chart(df: pd.DataFrame) -> None:
    st.subheader("Sessions by Project")

    _, hues, surface, text_primary, text_secondary, _ = _theme_colors()
    domain, color_range = _project_color_scale(df, hues)

    total_sessions = int(df["Sessions"].sum())

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "background": None,
        "width": 320,
        "height": 320,
        "view": {"stroke": None},
        "config": {
            "font": "system-ui, -apple-system, 'Segoe UI', sans-serif",
            "legend": {"labelColor": text_secondary, "labelFontSize": 12},
        },
        "layer": [
            {
                "data": {"values": df.to_dict("records")},
                "mark": {
                    "type": "arc",
                    "innerRadius": 70,
                    "outerRadius": 150,
                    "stroke": surface,
                    "strokeWidth": 2,
                },
                "encoding": {
                    "theta": {"field": "Sessions", "type": "quantitative"},
                    "order": {"field": "Sessions", "sort": "descending"},
                    "color": {
                        "field": "Project",
                        "type": "nominal",
                        "scale": {"domain": domain, "range": color_range},
                        "legend": {"title": None, "orient": "right"},
                    },
                    "tooltip": [
                        {"field": "Project", "type": "nominal"},
                        {"field": "Sessions", "type": "quantitative"},
                        {"field": "Percent", "type": "nominal", "title": "Share"},
                    ],
                },
            },
            {
                "data": {"values": [{"label": str(total_sessions)}]},
                "mark": {
                    "type": "text",
                    "fontSize": 30,
                    "fontWeight": 600,
                    "color": text_primary,
                },
                "encoding": {"text": {"field": "label", "type": "nominal"}},
            },
            {
                "data": {"values": [{"label": "sessions"}]},
                "mark": {
                    "type": "text",
                    "dy": 24,
                    "fontSize": 12,
                    "color": text_secondary,
                },
                "encoding": {"text": {"field": "label", "type": "nominal"}},
            },
        ],
    }

    st.vega_lite_chart(spec, width="stretch")


def _render_messages_cost_chart(
    df: pd.DataFrame,
    project_order: list[str],
    hues: Sequence[str],
    text_secondary: str,
    grid: str,
) -> None:
    """Messages and cost per project as grouped bars, each normalized to % of its own max."""
    # Messages and cost live on very different scales - normalizing each to
    # its own max (instead of a dual-axis chart, which invents a fake
    # correlation between independent scales) lets both share one 0-100% axis.
    st.subheader("Messages & Cost by Project")

    max_messages = df["Messages"].max() or 1
    max_cost = df["Cost"].max() or 1
    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "Project": row["Project"],
                "Metric": "Messages",
                "Pct": 100 * row["Messages"] / max_messages,
                "Formatted": f"{int(row['Messages']):,}",
            }
        )
        records.append(
            {
                "Project": row["Project"],
                "Metric": "Cost",
                "Pct": 100 * row["Cost"] / max_cost,
                "Formatted": f"${row['Cost']:,.2f}",
            }
        )

    metric_domain = ["Messages", "Cost"]
    metric_colors = [hues[0], hues[1]]

    st.caption(
        "Each metric is shown as a % of its own top project (e.g. a Cost bar "
        "at 50% means that project cost half as much as the priciest project) "
        "- Messages and Cost are scaled independently."
    )

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "background": None,
        "width": 700,
        "height": 300,
        "view": {"stroke": None},
        "config": {
            "font": "system-ui, -apple-system, 'Segoe UI', sans-serif",
            "legend": {"labelColor": text_secondary, "labelFontSize": 12},
        },
        "data": {"values": records},
        "encoding": {
            "x": {
                "field": "Project",
                "type": "nominal",
                "sort": project_order,
                "title": None,
                "axis": {
                    "domain": False,
                    "ticks": False,
                    "labelColor": text_secondary,
                    "labelFontSize": 11,
                    "labelAngle": -25,
                    "labelLimit": 120,
                },
            },
            "xOffset": {"field": "Metric", "sort": metric_domain},
            "y": {
                "field": "Pct",
                "type": "quantitative",
                "title": "% of top project",
                "scale": {"domain": [0, 115]},
                "axis": {
                    "domain": False,
                    "gridColor": grid,
                    "labelColor": text_secondary,
                    "labelFontSize": 10,
                    "titleColor": text_secondary,
                    "values": [0, 25, 50, 75, 100],
                },
            },
        },
        "layer": [
            {
                "mark": {
                    "type": "bar",
                    "cornerRadiusTopLeft": 3,
                    "cornerRadiusTopRight": 3,
                },
                "encoding": {
                    "color": {
                        "field": "Metric",
                        "type": "nominal",
                        "scale": {"domain": metric_domain, "range": metric_colors},
                        "legend": {"title": None, "orient": "top"},
                    },
                    "tooltip": [
                        {"field": "Project", "type": "nominal"},
                        {"field": "Metric", "type": "nominal"},
                        {"field": "Formatted", "type": "nominal", "title": "Value"},
                    ],
                },
            },
            {
                "mark": {
                    "type": "text",
                    "dy": -6,
                    "baseline": "bottom",
                    "fontSize": 9,
                },
                "encoding": {
                    "text": {"field": "Formatted", "type": "nominal"},
                    "color": {"value": text_secondary},
                },
            },
        ],
    }

    st.vega_lite_chart(spec, width="stretch")


def _render_hourly_activity_chart(
    df: pd.DataFrame, hues: Sequence[str], text_secondary: str, grid: str
) -> None:
    """Sessions and messages by local hour, as grouped bars normalized to % of each metric's max."""
    # Same normalize-to-own-max approach as _render_messages_cost_chart above,
    # to avoid a dual-axis chart between two independently-scaled metrics.
    st.subheader("Activity by Hour of Day")

    hour_order = list(df["Label"])
    max_sessions = df["Sessions"].max() or 1
    max_messages = df["Messages"].max() or 1
    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "Label": row["Label"],
                "Metric": "Sessions",
                "Pct": 100 * row["Sessions"] / max_sessions,
                "Formatted": f"{int(row['Sessions']):,}",
            }
        )
        records.append(
            {
                "Label": row["Label"],
                "Metric": "Messages",
                "Pct": 100 * row["Messages"] / max_messages,
                "Formatted": f"{int(row['Messages']):,}",
            }
        )

    # "Messages" keeps the same hue it has in the messages/cost chart above
    # (color follows the entity, not the chart it's drawn in).
    metric_domain = ["Sessions", "Messages"]
    metric_colors = [hues[1], hues[0]]

    st.caption(
        "Each metric is shown as a % of its own busiest hour (e.g. a Sessions "
        "bar at 50% means that hour had half as many sessions as the busiest "
        "hour for sessions) - Sessions and Messages are scaled independently."
    )

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "background": None,
        "width": 760,
        "height": 260,
        "view": {"stroke": None},
        "config": {
            "font": "system-ui, -apple-system, 'Segoe UI', sans-serif",
            "legend": {"labelColor": text_secondary, "labelFontSize": 12},
        },
        "data": {"values": records},
        "mark": {"type": "bar", "cornerRadiusTopLeft": 3, "cornerRadiusTopRight": 3},
        "encoding": {
            "x": {
                "field": "Label",
                "type": "nominal",
                "sort": hour_order,
                "title": None,
                "axis": {
                    "domain": False,
                    "ticks": False,
                    "labelAngle": 0,
                    "labelColor": text_secondary,
                    "labelFontSize": 9,
                    "labelOverlap": "parity",
                },
            },
            "xOffset": {"field": "Metric", "sort": metric_domain},
            "y": {
                "field": "Pct",
                "type": "quantitative",
                "title": "% of busiest hour",
                "axis": {
                    "domain": False,
                    "gridColor": grid,
                    "labelColor": text_secondary,
                    "labelFontSize": 10,
                    "titleColor": text_secondary,
                    "values": [0, 25, 50, 75, 100],
                },
            },
            "color": {
                "field": "Metric",
                "type": "nominal",
                "scale": {"domain": metric_domain, "range": metric_colors},
                "legend": {"title": None, "orient": "top"},
            },
            "tooltip": [
                {"field": "Label", "type": "nominal", "title": "Hour"},
                {"field": "Metric", "type": "nominal"},
                {"field": "Formatted", "type": "nominal", "title": "Value"},
            ],
        },
    }

    st.vega_lite_chart(spec, width="stretch")


def render_overview_page() -> None:
    transcripts = load_transcripts()
    if not transcripts:
        st.write("No Claude session transcripts found.")
        return

    st.header("Overview")
    range_label = (
        st.segmented_control(
            "Time range",
            options=list(_TIME_RANGES),
            default="All time",
            key="overview_time_range",
            label_visibility="collapsed",
            width="stretch",
        )
        or "All time"
    )

    filtered = _filter_transcripts_by_range(transcripts, range_label)
    if not filtered:
        st.write(f"No Claude session transcripts found for {range_label.lower()}.")
        return

    df = _project_totals_dataframe(filtered)
    chart_col, stats_col = st.columns([1, 1])

    with stats_col:
        _render_summary_stats(filtered)

    with chart_col:
        _render_project_sessions_chart(df)

    _, hues, _, _, text_secondary, grid = _theme_colors()
    domain, _ = _project_color_scale(df, hues)

    _render_messages_cost_chart(df, domain, hues, text_secondary, grid)

    _render_hourly_activity_chart(
        _hourly_activity_dataframe(filtered), hues, text_secondary, grid
    )
