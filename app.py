import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import config as st_config

from claude_projects import delete_project, load_projects
from claude_sessions import load_sessions
from claude_transcripts import delete_project_transcripts, delete_transcript, load_transcripts

_THEME_PREF_PATH = Path(__file__).parent / ".streamlit" / "theme_pref.json"


def _load_theme_pref() -> str:
    try:
        data = json.loads(_THEME_PREF_PATH.read_text())
        return "dark" if data.get("dark") else "light"
    except (OSError, ValueError):
        return st_config.get_option("theme.base")


def _persist_theme(theme: str) -> None:
    try:
        _THEME_PREF_PATH.write_text(json.dumps({"dark": theme == "dark"}))
    except OSError:
        pass


def _sessions_dataframe() -> pd.DataFrame:
    sessions = load_sessions()
    return pd.DataFrame(
        [
            {
                "Name": s.name,
                "Project": s.project,
                "Status": s.status,
                "Kind": s.kind,
                "PID": s.pid,
                "Started": s.started_at,
                "Last Updated": s.updated_at,
                "Session ID": s.session_id,
            }
            for s in sessions
        ]
    )


def _transcripts_dataframe() -> pd.DataFrame:
    transcripts = load_transcripts()
    return pd.DataFrame(
        [
            {
                "Project": t.project,
                "Session ID": t.session_id,
                "Started": t.started_at,
                "Last Updated": t.updated_at,
                "Messages": t.message_count,
                "Est. Cost ($)": t.cost,
                "Version": t.version,
                "Git Branch": t.git_branch,
            }
            for t in transcripts
        ]
    )


def _projects_dataframe() -> pd.DataFrame:
    projects = load_projects()
    return pd.DataFrame(
        [
            {
                "Name": p.name,
                "Path": p.path,
                "Trusted": p.trust_accepted,
                "Last Session": p.last_session_id,
                "Version": p.last_version,
                "Last Cost ($)": p.last_cost,
                "Last Started": p.last_start_time,
                "Lines +/-": (
                    f"+{p.lines_added}/-{p.lines_removed}"
                    if p.lines_added is not None or p.lines_removed is not None
                    else None
                ),
                "MCP Servers": ", ".join(p.mcp_servers) if p.mcp_servers else None,
            }
            for p in projects
        ]
    )


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


def _clear_project(project_path: str) -> None:
    """Remove a project's ~/.claude.json entry and its on-disk transcripts."""
    delete_project(project_path)
    delete_project_transcripts(project_path)
    st.session_state.projects_df = _projects_dataframe()
    st.session_state.projects_refreshed_at = datetime.now()
    st.session_state.pop("confirm_delete_project", None)
    st.session_state.clear_projects_table_selection = True


def render_projects_table() -> None:
    if "projects_df" not in st.session_state:
        st.session_state.projects_df = _projects_dataframe()
        st.session_state.projects_refreshed_at = datetime.now()
    # st.dataframe's selection can only be reset via session_state before the
    # widget with this key is (re-)instantiated below, not after (Streamlit
    # raises StreamlitWidgetAlreadyInstantiatedError) - hence the flag/rerun.
    if st.session_state.pop("clear_projects_table_selection", False):
        st.session_state["projects_table"] = {"selection": {"rows": [], "columns": []}}

    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("⟳"):
            st.session_state.projects_df = _projects_dataframe()
            st.session_state.projects_refreshed_at = datetime.now()
        st.caption(f"Last refreshed: {st.session_state.projects_refreshed_at:%H:%M:%S}")
        st.toggle("Edit mode", key="projects_delete_mode")

    df = st.session_state.projects_df
    if df.empty:
        st.write("No Claude projects found.")
        return

    if not st.session_state.projects_delete_mode:
        st.dataframe(df, width="stretch", hide_index=True)
        return

    event = st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="projects_table",
    )
    selected_rows = event.selection.rows if event else []

    if selected_rows:
        selected_path = df.iloc[selected_rows[0]]["Path"]
        if st.button(f"🗑️ Delete '{selected_path}'"):
            st.session_state.confirm_delete_project = selected_path

    confirm_path = st.session_state.get("confirm_delete_project")
    if confirm_path:
        st.warning(
            f"Delete project '{confirm_path}' from ~/.claude.json and remove all "
            "of its on-disk session transcripts? This cannot be undone."
        )
        with st.container(horizontal=True):
            if st.button("Confirm delete", type="primary"):
                _clear_project(confirm_path)
                st.rerun()
            if st.button("Cancel"):
                st.session_state.pop("confirm_delete_project", None)
                st.rerun()


def render_transcripts_table() -> None:
    if "transcripts_df" not in st.session_state:
        st.session_state.transcripts_df = _transcripts_dataframe()
        st.session_state.transcripts_refreshed_at = datetime.now()
    # st.dataframe's selection can only be reset via session_state before the
    # widget with this key is (re-)instantiated below, not after (Streamlit
    # raises StreamlitWidgetAlreadyInstantiatedError) - hence the flag/rerun.
    if st.session_state.pop("clear_transcripts_table_selection", False):
        st.session_state["transcripts_table"] = {
            "selection": {"rows": [], "columns": []}
        }

    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("⟳", key="transcripts_refresh"):
            st.session_state.transcripts_df = _transcripts_dataframe()
            st.session_state.transcripts_refreshed_at = datetime.now()
        st.caption(
            f"Last refreshed: {st.session_state.transcripts_refreshed_at:%H:%M:%S}"
        )
        st.toggle("Edit mode", key="transcripts_delete_mode")

    df = st.session_state.transcripts_df
    if df.empty:
        st.write("No Claude session transcripts found.")
        return

    if not st.session_state.transcripts_delete_mode:
        st.dataframe(df, width="stretch", hide_index=True)
        return

    event = st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="transcripts_table",
    )
    selected_rows = event.selection.rows if event else []
    selected_ids = list(df.iloc[selected_rows]["Session ID"]) if selected_rows else []

    # Live sessions are still being written to by a running process, so
    # they can't be deleted even if their row gets selected.
    live_ids = {s.session_id for s in load_sessions()}
    live_selected = [sid for sid in selected_ids if sid in live_ids]
    selected_ids = [sid for sid in selected_ids if sid not in live_ids]

    if live_selected:
        st.caption(
            f"{len(live_selected)} selected session(s) are still live and can't be deleted."
        )

    if selected_ids:
        if st.button(f"🗑️ Delete {len(selected_ids)} selected session(s)"):
            st.session_state.confirm_delete_transcripts = selected_ids

    confirm_ids = st.session_state.get("confirm_delete_transcripts")
    if confirm_ids:
        st.warning(
            f"Delete {len(confirm_ids)} selected session transcript(s)? "
            "This cannot be undone."
        )
        with st.container(horizontal=True):
            if st.button("Confirm delete", type="primary", key="confirm_delete_transcripts_btn"):
                for session_id in confirm_ids:
                    delete_transcript(session_id)
                st.session_state.transcripts_df = _transcripts_dataframe()
                st.session_state.transcripts_refreshed_at = datetime.now()
                st.session_state.pop("confirm_delete_transcripts", None)
                st.session_state.clear_transcripts_table_selection = True
                st.rerun()
            if st.button("Cancel", key="cancel_delete_transcripts_btn"):
                st.session_state.pop("confirm_delete_transcripts", None)
                st.rerun()


@st.fragment(run_every="2s")
def render_sessions_table() -> None:
    first_load = "sessions_df" not in st.session_state
    if first_load:
        st.session_state.sessions_df = _sessions_dataframe()
        st.session_state.sessions_refreshed_at = datetime.now()

    with st.container(horizontal=True, vertical_alignment="center"):
        st.toggle("Auto-refresh", value=True, key="auto_refresh")
        st.caption(f"Last refreshed: {st.session_state.sessions_refreshed_at:%H:%M:%S}")

    if not first_load and st.session_state.auto_refresh:
        st.session_state.sessions_df = _sessions_dataframe()
        st.session_state.sessions_refreshed_at = datetime.now()

    df = st.session_state.sessions_df
    if df.empty:
        st.write("No Claude sessions found.")
    else:
        st.dataframe(df, width="stretch", hide_index=True)


_COMPACT_LAYOUT_CSS = """
<style>
[data-testid="stHeader"] {
    height: 0rem;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 1rem;
    padding-left: 2rem;
    padding-right: 2rem;
}
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] hr) {
    height: 2rem;
}
[data-testid="stMarkdownContainer"] hr {
    margin: 0.9375rem 0;
}
</style>
"""


def _set_page(page: str) -> None:
    st.session_state.page = page


def main() -> None:
    st.set_page_config(page_title="The Ledger", page_icon="🤖", layout="wide")
    st.markdown(_COMPACT_LAYOUT_CSS, unsafe_allow_html=True)

    if "page" not in st.session_state:
        st.session_state.page = "sessions"

    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown("**The Ledger**")
        # Set page via on_click (not the button's return value) so the state
        # update happens before this rerun renders the buttons - otherwise
        # the type=primary/secondary highlight is computed from the stale
        # pre-click page and lags one click behind.
        st.button(
            "Overview",
            type="primary" if st.session_state.page == "overview" else "secondary",
            on_click=_set_page,
            args=("overview",),
        )
        st.button(
            "Sessions",
            type="primary" if st.session_state.page == "sessions" else "secondary",
            on_click=_set_page,
            args=("sessions",),
        )
        st.button(
            "Projects",
            type="primary" if st.session_state.page == "projects" else "secondary",
            on_click=_set_page,
            args=("projects",),
        )

        st.caption("")

        dark_mode = st.toggle(
            "Dark mode",
            value=_load_theme_pref() == "dark",
            key="dark_mode",
        )
    st.divider()

    desired_theme = "dark" if dark_mode else "light"
    if st_config.get_option("theme.base") != desired_theme:
        st_config.set_option("theme.base", desired_theme)
        _persist_theme(desired_theme)
        st.rerun()

    if st.session_state.page == "overview":
        st.header("Overview")
        render_overview_page()

    elif st.session_state.page == "sessions":
        st.header("Sessions")
        st.subheader("Live")
        render_sessions_table()

        st.subheader("All")
        render_transcripts_table()

    else:
        st.header("Projects")
        render_projects_table()


if __name__ == "__main__":
    from streamlit import runtime
    from streamlit.web import cli as stcli

    if runtime.exists():
        main()
    else:
        # Allow `python app.py` to work the same as `streamlit run app.py`
        # by relaunching this file under the Streamlit server.
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
