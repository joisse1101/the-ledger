from datetime import datetime

import pandas as pd
import streamlit as st

from claude_projects import delete_project, load_projects
from claude_transcripts import delete_project_transcripts


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
