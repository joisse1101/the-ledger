from typing import Sequence

import pandas as pd
import streamlit as st
from streamlit import config as st_config

from claude_transcripts import ClaudeTranscript, load_transcripts

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


def _project_session_counts_dataframe(
    transcripts: Sequence[ClaudeTranscript], top_n: int = _MAX_PROJECT_SLICES
) -> pd.DataFrame:
    """Session counts per project, from every on-disk transcript ever run."""
    counts: dict[str, int] = {}
    for t in transcripts:
        counts[t.project] = counts.get(t.project, 0) + 1
    if not counts:
        return pd.DataFrame(columns=["Project", "Sessions", "Percent"])

    ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    head, tail = ordered[:top_n], ordered[top_n:]
    rows = [{"Project": name, "Sessions": n} for name, n in head]
    if tail:
        rows.append({"Project": "Other", "Sessions": sum(n for _, n in tail)})

    total = sum(r["Sessions"] for r in rows)
    for r in rows:
        r["Percent"] = f"{100 * r['Sessions'] / total:.1f}%"
    return pd.DataFrame(rows)


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


def render_overview_page() -> None:
    st.subheader("Sessions by project")

    transcripts = load_transcripts()
    if not transcripts:
        st.write("No Claude session transcripts found.")
        return

    df = _project_session_counts_dataframe(transcripts)
    chart_col, stats_col = st.columns([1, 1])

    with stats_col:
        _render_summary_stats(transcripts)

    is_dark = st_config.get_option("theme.base") == "dark"
    hues = _CATEGORICAL_DARK if is_dark else _CATEGORICAL_LIGHT
    surface = "#1a1a19" if is_dark else "#fcfcfb"
    text_primary = "#ffffff" if is_dark else "#0b0b0b"
    text_secondary = "#c3c2b7" if is_dark else "#52514e"

    domain = list(df["Project"])
    has_other = "Other" in domain
    n_named = len(domain) - (1 if has_other else 0)
    color_range = hues[:n_named] + ([_MUTED_INK] if has_other else [])

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
    with chart_col:
        st.vega_lite_chart(spec, width="stretch")
