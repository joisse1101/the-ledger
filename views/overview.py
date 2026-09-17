import pandas as pd
import streamlit as st
from streamlit import config as st_config

from claude_transcripts import load_transcripts

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


def _project_session_counts_dataframe(top_n: int = _MAX_PROJECT_SLICES) -> pd.DataFrame:
    """Session counts per project, from every on-disk transcript ever run."""
    counts: dict[str, int] = {}
    for t in load_transcripts():
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


def render_overview_page() -> None:
    st.subheader("Sessions by project")
    df = _project_session_counts_dataframe()
    if df.empty:
        st.write("No Claude session transcripts found.")
        return

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
    st.vega_lite_chart(spec, width="stretch")
