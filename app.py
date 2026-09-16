import sys

import streamlit as st


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
        st.write("Sessions page (placeholder).")
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
