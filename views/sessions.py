from datetime import datetime

import pandas as pd
import streamlit as st

from claude_sessions import load_sessions
from claude_transcripts import delete_transcript, load_transcripts


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
