import sys
from datetime import datetime

import pandas as pd
import streamlit as st

from claude_sessions import load_sessions


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


@st.fragment(run_every="2s")
def render_sessions_table() -> None:
    st.toggle("Auto-refresh", value=True, key="auto_refresh")

    if st.session_state.auto_refresh or "sessions_df" not in st.session_state:
        st.session_state.sessions_df = _sessions_dataframe()
        st.session_state.sessions_refreshed_at = datetime.now()

    st.caption(f"Last refreshed: {st.session_state.sessions_refreshed_at:%H:%M:%S}")

    df = st.session_state.sessions_df
    if df.empty:
        st.write("No Claude sessions found.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Claude Manager", page_icon="🤖", layout="wide")

    if "page" not in st.session_state:
        st.session_state.page = "sessions"

    with st.sidebar:
        st.header("Navigation")
        if st.button("Sessions", use_container_width=True):
            st.session_state.page = "sessions"
        if st.button("Projects", use_container_width=True):
            st.session_state.page = "projects"

    if st.session_state.page == "sessions":
        st.header("Sessions")
        render_sessions_table()
    else:
        st.header("Projects")
        st.write("Projects page (placeholder).")


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
