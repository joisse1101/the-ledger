from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

import pandas as pd
import streamlit as st
from streamlit import config as st_config

from claude_transcripts import ClaudeTranscript, load_transcripts

# Time-range filter options for the summary stats/chart, in display order.
# "All time" (None) skips filtering entirely.
_TIME_RANGES: dict[str, Optional[timedelta]] = {
    "All time": None,
    "Past week": timedelta(days=7),
    "Past month": timedelta(days=30),
    "Past quarter": timedelta(days=90),
    "Past year": timedelta(days=365),
}

# Fixed-order categorical palette (validated for adjacent-pair CVD safety);
# see the dataviz skill's references/palette.md. Slot order must never be
# re-sorted per-chart - only which prefix of it is used may vary.
_CATEGORICAL_LIGHT = [
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
    "#4a3aa7",
    "#e34948",
]
_CATEGORICAL_DARK = [
    "#3987e5",
    "#d95926",
    "#199e70",
    "#c98500",
    "#d55181",
    "#008300",
    "#9085e9",
    "#e66767",
]
_MUTED_INK = "#898781"  # "Other" bucket - same in both modes
_MAX_PROJECT_SLICES = 7  # beyond this, fold the tail into "Other"


def _filter_transcripts_by_range(
    transcripts: Sequence[ClaudeTranscript], range_label: str
) -> Sequence[ClaudeTranscript]:
    """Transcripts whose activity falls within the chosen time range.

    A session is placed by its start time (falling back to its last-updated
    time for the rare transcript with no parsed start), not its update time,
    so a still-running session is bucketed by when it began.
    """
    delta = _TIME_RANGES.get(range_label)
    if delta is None:
        return transcripts
    cutoff = datetime.now(timezone.utc) - delta
    result = []
    for t in transcripts:
        anchor = t.started_at or t.updated_at
        if anchor is not None and anchor >= cutoff:
            result.append(t)
    return result


def _project_totals_dataframe(
    transcripts: Sequence[ClaudeTranscript], top_n: int = _MAX_PROJECT_SLICES
) -> pd.DataFrame:
    """Per-project totals (sessions/messages/cost), folded into the same top-N
    + "Other" split (ranked by session count) for every project chart on this
    page, so a project's color/identity never shifts between charts."""
    totals: dict[str, dict] = {}
    for t in transcripts:
        row = totals.setdefault(t.project, {"Sessions": 0, "Messages": 0, "Cost": 0.0})
        row["Sessions"] += 1
        row["Messages"] += t.message_count
        row["Cost"] += t.cost
    if not totals:
        return pd.DataFrame(
            columns=["Project", "Sessions", "Messages", "Cost", "Percent"]
        )

    ordered = sorted(totals.items(), key=lambda kv: kv[1]["Sessions"], reverse=True)
    head, tail = ordered[:top_n], ordered[top_n:]
    rows = [{"Project": name, **vals} for name, vals in head]
    if tail:
        rows.append(
            {
                "Project": "Other",
                "Sessions": sum(v["Sessions"] for _, v in tail),
                "Messages": sum(v["Messages"] for _, v in tail),
                "Cost": sum(v["Cost"] for _, v in tail),
            }
        )

    total_sessions = sum(r["Sessions"] for r in rows)
    for r in rows:
        r["Percent"] = f"{100 * r['Sessions'] / total_sessions:.1f}%"
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
    """Domain/range for a Project color encoding, shared across all project
    charts so the same project always gets the same hue."""
    domain = list(df["Project"])
    has_other = "Other" in domain
    n_named = len(domain) - (1 if has_other else 0)
    color_range = list(hues[:n_named]) + ([_MUTED_INK] if has_other else [])
    return domain, color_range


def _format_hour(hour: int) -> str:
    period = "a" if hour < 12 else "p"
    display = hour % 12 or 12
    return f"{display}{period}"


def _hourly_activity_dataframe(transcripts: Sequence[ClaudeTranscript]) -> pd.DataFrame:
    """Per-hour-of-day totals (session count and message count), bucketed by
    each transcript's local start time. All 24 hours are always present
    (zero-filled) so the histogram never looks like it's missing a category."""
    sessions = [0] * 24
    messages = [0] * 24
    for t in transcripts:
        anchor = t.started_at or t.updated_at
        if anchor is None:
            continue
        hour = anchor.astimezone().hour
        sessions[hour] += 1
        messages[hour] += t.message_count
    return pd.DataFrame(
        {
            "Label": [_format_hour(h) for h in range(24)],
            "Sessions": sessions,
            "Messages": messages,
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
    num_projects = len({t.project for t in transcripts})
    num_sessions = len(transcripts)
    total_messages = sum(t.message_count for t in transcripts)

    durations = [
        ((t.updated_at - t.started_at).total_seconds(), t)
        for t in transcripts
        if t.started_at and t.updated_at
    ]

    costs = [(t.cost, t) for t in transcripts]

    total = sum(d for d, _ in durations)
    avg_seconds = total / len(durations) if durations else 0
    longest = max(durations, key=lambda d: d[0]) if durations else None
    shortest = min(durations, key=lambda d: d[0]) if durations else None

    total_cost = sum(c for c, _ in costs)
    most_expensive = max(costs, key=lambda c: c[0])[1] if costs else None
    avg_cost = total_cost / len(costs) if costs else 0
    cheapest = min(costs, key=lambda c: c[0])[1] if costs else None

    def _session_help(entry: tuple[float, ClaudeTranscript] | None) -> str | None:
        if entry is None:
            return None
        _, t = entry
        # st.metric's help text renders as markdown - a bare "\n" is collapsed,
        # so a trailing two-space "hard break" is needed for an actual line break.
        return f"{t.project}  \n{t.session_id}"

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
    """Messages and cost per project as grouped bars on one shared axis.

    Messages and cost sit on very different scales, so instead of a literal
    dual-axis chart (flagged as the #1 charting mistake - the alignment of two
    independent scales is arbitrary and invents a correlation that isn't in
    the data), each metric is normalized to % of its own max. Both then share
    one 0-100% axis and stay directly comparable.
    """
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
    """Sessions and messages by local hour of day, as grouped bars on one
    shared axis - same normalize-to-%-of-max approach as the messages/cost
    chart, so the two metrics' very different scales don't need dual axes.
    """
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
