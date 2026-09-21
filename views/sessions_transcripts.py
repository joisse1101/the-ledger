"""All-transcripts table, filters, and sort controls."""

import streamlit as st

from claude_sessions import load_sessions
from views.sessions_data import (_categorical_options, _filter_transcripts_dataframe,
                                 _sort_transcripts_dataframe, _transcripts_dataframe)
from views.sessions_dialog import _maybe_render_recap_dialog, _open_session_dialog
from views.sessions_table import (_ROW_CSS, _render_sortable_table_header,
                                  _render_table_row, _tooltip_text)


_TRANSCRIPTS_COLUMNS = ["Project", "Title", "Session ID", "Started", "Last Updated", "Messages", "Est. Cost ($)", "Version", "Git Branch"]
_TRANSCRIPTS_WIDTHS = [3, 3, 4, 3, 3, 2, 2, 2, 2]
_TRANSCRIPTS_SORT_STATE_KEY = "transcripts_sort"
_TRANSCRIPTS_DEFAULT_SORT = ("Last Updated", False)


def _clear_transcripts_search() -> None:
    st.session_state.pop("transcripts_search", None)
    st.session_state.pop("transcripts_table", None)


def render_transcripts_table() -> None:
    st.markdown(_ROW_CSS, unsafe_allow_html=True)
    df = _transcripts_dataframe()
    if df.empty:
        st.write("No Claude session transcripts found.")
        _maybe_render_recap_dialog("transcripts")
        return

    st.session_state.setdefault(_TRANSCRIPTS_SORT_STATE_KEY, _TRANSCRIPTS_DEFAULT_SORT)
    with st.container(gap="xxsmall"):
        with st.container(horizontal=True, vertical_alignment="bottom"):
            search = st.text_input(
                "Search Session ID, Last Message or First Prompt",
                key="transcripts_search",
                placeholder="Session ID, Last Message or First Prompt contains…",
            )
            st.button("Clear", key="clear_transcripts_search", on_click=_clear_transcripts_search)
        with st.container(horizontal=True, vertical_alignment="bottom"):
            projects = st.multiselect("Project", _categorical_options(df, "Project"), key="transcripts_filter_project", placeholder="Select projects…", label_visibility="collapsed")
            versions = st.multiselect("Version", _categorical_options(df, "Version"), key="transcripts_filter_version", placeholder="Select versions…", label_visibility="collapsed")
            branches = st.multiselect("Git Branch", _categorical_options(df, "Git Branch"), key="transcripts_filter_branch", placeholder="Select branches…", label_visibility="collapsed")
    df = _filter_transcripts_dataframe(df, search=search, projects=projects, versions=versions, branches=branches)
    sort_column, ascending = st.session_state[_TRANSCRIPTS_SORT_STATE_KEY]
    df = _sort_transcripts_dataframe(df, sort_column, ascending)
    st.caption("Click a session to see what it was about.")
    live_ids = {session.session_id for session in load_sessions()}
    if df.empty:
        st.write("No sessions match the current filters.")
        _maybe_render_recap_dialog("transcripts")
        return

    with st.container(gap="xxsmall"):
        _render_sortable_table_header(_TRANSCRIPTS_COLUMNS, _TRANSCRIPTS_WIDTHS, key="table-header-transcripts", sort_state_key=_TRANSCRIPTS_SORT_STATE_KEY)
        st.divider()
        for row in df.to_dict("records"):
            _render_table_row(
                row,
                _TRANSCRIPTS_COLUMNS,
                _TRANSCRIPTS_WIDTHS,
                key=f"sessrow-transcripts-{row['Session ID']}",
                tooltip=_tooltip_text(row, "transcripts"),
                on_click=lambda r=row: _open_session_dialog(
                    source="transcripts",
                    heading=f"[{r['Project']}] {r['Git Branch']}",
                    session_id=r["Session ID"],
                    title=r["Title"],
                    last_message=r["Last Message"],
                    first_prompt=r["First Prompt"],
                    started=r["Started"],
                    updated=r["Last Updated"],
                    deletable=r["Session ID"] not in live_ids,
                ),
            )
    _maybe_render_recap_dialog("transcripts")
