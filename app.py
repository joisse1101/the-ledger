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
    """Whether _auto_refresh_data should actually refresh() on this call.

    False on the very first-ever call (last is None - main() already seeds
    the snapshot before _auto_refresh_data runs, so there's nothing to redo)
    and on any call less than _AUTO_REFRESH_INTERVAL after the last refresh.
    """
    return last is not None and now - last >= _AUTO_REFRESH_INTERVAL


@st.fragment(run_every="10m")
def _auto_refresh_data() -> None:
    """Silently re-run claude_db.refresh() every 10 minutes so the nav bar's
    "Last refreshed" caption (and every page reading from the shared
    snapshot) stays current without anyone clicking the "⟳" button.
    """
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

        # The help tooltip is set from refreshed_at() *before* the button is
        # drawn, so a click can't update its own tooltip text in the same
        # pass - st.rerun() re-executes this block immediately after
        # refresh() so the tooltip picks up the new timestamp right away,
        # instead of lagging one click behind. The key is timestamp-based
        # (not a fixed string) so that rerun also remounts the button as a
        # fresh DOM node - otherwise React patches the existing node in
        # place, and since the mouse never actually left it, the open
        # tooltip's hover state has no mouseleave to reset it and gets
        # stuck showing even after the cursor moves away.
        if st.button("⟳", key=f"refresh_data", help="Refresh data from Claude files"):
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
