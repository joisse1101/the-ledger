import sys

import pandas as pd
import streamlit as st

from claude_sessions import load_sessions


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
        sessions = load_sessions()

        if not sessions:
            st.write("No Claude sessions found.")
        else:
            df = pd.DataFrame(
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
            st.dataframe(df, use_container_width=True, hide_index=True)
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
