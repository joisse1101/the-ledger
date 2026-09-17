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
[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
}
</style>
"""


def main() -> None:
    st.set_page_config(page_title="The Ledger", page_icon="🤖", layout="wide")
    st.markdown(_COMPACT_LAYOUT_CSS, unsafe_allow_html=True)

    if "page" not in st.session_state:
        st.session_state.page = "sessions"

    with st.sidebar:
        st.header("Navigation")
        if st.button("Sessions", width="stretch"):
            st.session_state.page = "sessions"
        if st.button("Projects", width="stretch"):
            st.session_state.page = "projects"
        st.divider()
        dark_mode = st.toggle(
            "Dark mode",
            value=_load_theme_pref() == "dark",
            key="dark_mode",
        )

    desired_theme = "dark" if dark_mode else "light"
    if st_config.get_option("theme.base") != desired_theme:
        st_config.set_option("theme.base", desired_theme)
        _persist_theme(desired_theme)
        st.rerun()

    if st.session_state.page == "sessions":
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
