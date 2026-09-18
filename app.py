import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import streamlit as st
from streamlit import config as st_config

import claude_db
from views.overview import render_overview_page
from views.projects import render_projects_table
from views.sessions import render_sessions_table, render_transcripts_table

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


_AUTO_REFRESH_INTERVAL = timedelta(minutes=10)


def _auto_refresh_due(last: Optional[datetime], now: datetime) -> bool:
    """True once _AUTO_REFRESH_INTERVAL has passed since the last refresh."""
    # `last is None` means main() just seeded the snapshot - nothing to redo yet.
    return last is not None and now - last >= _AUTO_REFRESH_INTERVAL


@st.fragment(run_every="10m")
def _auto_refresh_data() -> None:
    """Re-run claude_db.refresh() every 10 minutes, in the background."""
    # This fragment call happens on *every* rerun (page nav, dark-mode toggle,
    # ...), not just its own 10m timer, so it can't unconditionally refresh()
    # + st.rerun() - that would loop forever on the very first call. Track
    # the last refresh ourselves and only act once the interval has elapsed.
    now = datetime.now()
    last = st.session_state.get("_last_auto_refresh")
    due = _auto_refresh_due(last, now)
    if last is not None and not due:
        return
    st.session_state["_last_auto_refresh"] = now
    if due:
        claude_db.refresh()
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="The Ledger", page_icon="🤖", layout="wide")
    st.markdown(_COMPACT_LAYOUT_CSS, unsafe_allow_html=True)

    if "page" not in st.session_state:
        st.session_state.page = "sessions"

    # Seed the shared SQLite snapshot on the very first run against a fresh
    # .streamlit/ledger.db, so the nav bar and pages aren't empty before
    # anyone has clicked refresh yet.
    if claude_db.refreshed_at() is None:
        claude_db.refresh()

    _auto_refresh_data()

    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown("**The Ledger**")
        # Set the page via on_click, not the button's return value, so the
        # primary/secondary highlight below reflects the click immediately
        # instead of lagging one rerun behind.
        st.button(
            "Overview",
            type="primary" if st.session_state.page == "overview" else "secondary",
            on_click=_set_page,
            args=("overview",),
        )
        st.button(
            "Manage Sessions",
            type="primary" if st.session_state.page == "sessions" else "secondary",
            on_click=_set_page,
            args=("sessions",),
        )
        st.button(
            "Manage Projects",
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

        # st.rerun() after refresh() re-runs this whole block, so the caption
        # below picks up the new timestamp immediately instead of lagging one
        # click behind.
        if st.button("⟳", key="refresh_data", help="Refresh data from Claude files"):
            claude_db.refresh()
            st.rerun()
        refreshed = claude_db.refreshed_at()
        last_refreshed = (
            f"Last refreshed: {refreshed:%H:%M:%S}" if refreshed else "Never refreshed"
        )
        st.caption(last_refreshed, width="content")

    st.divider()

    desired_theme = "dark" if dark_mode else "light"
    if st_config.get_option("theme.base") != desired_theme:
        st_config.set_option("theme.base", desired_theme)
        _persist_theme(desired_theme)
        st.rerun()

    if st.session_state.page == "overview":
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
