"""Auto-refreshing Live sessions table."""

from datetime import datetime

import streamlit as st

from views.sessions_context import _maybe_render_context_dialog, _open_context_dialog
from views.sessions_data import _sessions_dataframe
from views.sessions_table import _ROW_CSS, _render_table_header, _render_table_row, _tooltip_text


_LIVE_COLUMNS = ["Name", "Title", "Status", "Kind", "PID", "Context", "Session ID"]
_LIVE_WIDTHS = [2, 3, 1, 2, 1, 6, 4]


@st.fragment(run_every="2s")
def render_sessions_table() -> None:
    st.markdown(_ROW_CSS, unsafe_allow_html=True)
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
        st.caption("Click a session to see what filled its context.")
        with st.container(gap="xxsmall"):
            _render_table_header(_LIVE_COLUMNS, _LIVE_WIDTHS, key="table-header-live")
            st.divider()
            for row in df.to_dict("records"):
                _render_table_row(
                    row,
                    _LIVE_COLUMNS,
                    _LIVE_WIDTHS,
                    key=f"sessrow-live-{row['Session ID']}",
                    tooltip=_tooltip_text(row, "live"),
                    on_click=lambda r=row: _open_context_dialog(
                        session_id=r["Session ID"],
                        cwd=r["CWD"],
                        heading=f"[{r['Project']}] {r['Title'] or r['Name'] or r['Session ID']}",
                    ),
                )
    _maybe_render_context_dialog()
