from datetime import datetime
from typing import Sequence

import pandas as pd
import streamlit as st

from claude_sessions import load_sessions
from claude_transcripts import delete_transcript, load_transcripts

_LIVE_COLUMNS = [
    "Name",
    "Project",
    "Status",
    "Kind",
    "PID",
    "Started",
    "Last Updated",
    "Session ID",
]
_LIVE_WIDTHS = [3, 3, 2, 2, 1, 3, 3, 4]

_TRANSCRIPTS_COLUMNS = [
    "Project",
    "Session ID",
    "Started",
    "Last Updated",
    "Messages",
    "Est. Cost ($)",
    "Version",
    "Git Branch",
]
_TRANSCRIPTS_WIDTHS = [3, 4, 3, 3, 2, 2, 2, 2]


def _sessions_dataframe() -> pd.DataFrame:
    """The "Live" table's rows, one per running Claude Code session."""
    sessions = load_sessions()
    return pd.DataFrame(
        [
            {
                "Name": session.name,
                "Project": session.project,
                "Status": session.status,
                "Kind": session.kind,
                "PID": session.pid,
                "Started": session.started_at,
                "Last Updated": session.updated_at,
                "Session ID": session.session_id,
                "Recap": session.recap,
                "Recap Source": session.recap_source,
            }
            for session in sessions
        ]
    )


def _transcripts_dataframe() -> pd.DataFrame:
    """The "All" table's rows, one per session transcript ever recorded."""
    transcripts = load_transcripts()
    return pd.DataFrame(
        [
            {
                "Project": transcript.project,
                "Session ID": transcript.session_id,
                "Started": transcript.started_at,
                "Last Updated": transcript.updated_at,
                "Messages": transcript.message_count,
                "Est. Cost ($)": transcript.cost,
                "Version": transcript.version,
                "Git Branch": transcript.git_branch,
                "Recap": transcript.recap,
                "Recap Source": transcript.recap_source,
            }
            for transcript in transcripts
        ]
    )


# ---------------------------------------------------------------------------
# Custom clickable-row table.
#
# st.dataframe's built-in row selection only reacts to clicking its own
# checkbox column, not the row itself, and always shows that checkbox column
# whether or not it's wanted - not what we want here. Instead each row is a
# real st.container holding the cell text plus a same-size st.button
# stretched over it via CSS (position: absolute; inset: 0), so the row has no
# visible checkbox and is clickable/hoverable anywhere - opening the detail/
# actions dialog on click, and previewing the recap via the button's `help`
# tooltip on hover. Streamlit's own button styles set an explicit height on
# both the [data-testid="stButton"] wrapper and the <button> itself, which
# wins over our `inset: 0` stretch unless overridden - every level (wrapper,
# button, its inner label div) needs an explicit `!important` 100% height or
# the overlay collapses to the button's natural (small) size, leaving most of
# the row dead to hover/click.
# ---------------------------------------------------------------------------

_ROW_CSS = """
<style>
[class*="st-key-sessrow-"] {
    position: relative;
    border-bottom: 1px solid rgba(128, 128, 128, 0.18);
    padding: 0.35rem 0;
}
[class*="st-key-sessrow-"]:hover {
    background-color: rgba(128, 128, 128, 0.12);
}
[class*="st-key-sessrow-"] [data-testid="stElementContainer"]:has([data-testid="stButton"]) {
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
}
[class*="st-key-sessrow-"] [data-testid="stButton"] {
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
}
[class*="st-key-sessrow-"] [data-testid="stButton"] > div {
    width: 100% !important;
    height: 100% !important;
}
[class*="st-key-sessrow-"] [data-testid="stButton"] button {
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
    min-height: 100% !important;
    opacity: 0;
    cursor: pointer;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
}
[class*="st-key-table-header-"] {
    border-bottom: 2px solid rgba(128, 128, 128, 0.35);
    padding-bottom: 0.35rem;
    margin-bottom: 0.1rem;
    font-weight: 600;
}
</style>
"""


def _format_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _render_table_header(labels: Sequence[str], widths: Sequence[int], *, key: str) -> None:
    with st.container(key=key):
        for col, label in zip(st.columns(widths), labels):
            col.markdown(f"**{label}**")


def _render_table_row(
    row: dict,
    columns: Sequence[str],
    widths: Sequence[int],
    *,
    key: str,
    tooltip: str,
    on_click,
) -> None:
    with st.container(key=key):
        for col, name in zip(st.columns(widths, vertical_alignment="center"), columns):
            col.write(_format_cell(row[name]))
        if st.button("", key=f"{key}-btn", help=tooltip or None, use_container_width=True):
            on_click()


# ---------------------------------------------------------------------------
# What-was-this-about dialog, opened by clicking a row - shared by both
# tables. A dialog function only stays open across reruns if it keeps getting
# (re-)called - see the "Cast your vote" example in Streamlit's own st.dialog
# docs - so `recap_dialog_info` in session_state is the source of truth for
# "is a dialog open, and with what", and `_maybe_render_recap_dialog`
# re-invokes the dialog function on every rerun (including the Live table's
# 2s poll ticks) as long as it's still set. It's cleared by the dialog's own
# dismiss (`_dismiss_recap_dialog`, wired via on_dismiss) or by confirming/
# cancelling a delete.
# ---------------------------------------------------------------------------

_RECAP_SOURCE_LABELS = {
    "title": "Session title",
    "last_message": "Last message from Claude",
    "first_prompt": "First prompt",
}


def _open_session_dialog(
    *,
    source: str,
    title: str,
    project: str,
    session_id: str,
    recap: str,
    recap_source: str,
    deletable: bool,
) -> None:
    st.session_state.recap_dialog_info = {
        "source": source,
        "title": title,
        "project": project,
        "session_id": session_id,
        "recap": recap,
        "recap_source": recap_source,
        "deletable": deletable,
    }


def _dismiss_recap_dialog() -> None:
    st.session_state.recap_dialog_info = None
    st.session_state.pop("confirm_delete_session", None)


@st.dialog("Session details", on_dismiss=_dismiss_recap_dialog)
def _render_recap_dialog() -> None:
    info = st.session_state.get("recap_dialog_info")
    if not info:
        return

    st.markdown(f"**{info['title']}**")
    st.caption(f"{info['project']}  \n{info['session_id']}")

    if info["recap"]:
        label = _RECAP_SOURCE_LABELS.get(info["recap_source"])
        if label:
            st.caption(label)
        st.write(info["recap"])
    else:
        st.caption("No recap available yet for this session.")

    if info["source"] != "transcripts":
        return

    st.divider()
    if not info["deletable"]:
        st.caption("This session is still live and can't be deleted.")
        return

    if st.session_state.get("confirm_delete_session") == info["session_id"]:
        st.warning("Delete this session transcript? This cannot be undone.")
        with st.container(horizontal=True):
            if st.button("Confirm delete", type="primary", key="confirm_delete_session_btn"):
                delete_transcript(info["session_id"])
                st.session_state.pop("confirm_delete_session", None)
                st.session_state.recap_dialog_info = None
                st.rerun()
            if st.button("Cancel", key="cancel_delete_session_btn"):
                st.session_state.pop("confirm_delete_session", None)
                st.rerun()
    elif st.button("🗑️ Delete this session", key="open_delete_session_btn"):
        st.session_state.confirm_delete_session = info["session_id"]


def _maybe_render_recap_dialog(expected_source: str) -> None:
    info = st.session_state.get("recap_dialog_info")
    if info and info.get("source") == expected_source:
        _render_recap_dialog()


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
        st.caption("Click a session to see what it was about.")
        _render_table_header(_LIVE_COLUMNS, _LIVE_WIDTHS, key="table-header-live")
        for row in df.to_dict("records"):
            _render_table_row(
                row,
                _LIVE_COLUMNS,
                _LIVE_WIDTHS,
                key=f"sessrow-live-{row['Session ID']}",
                tooltip=row["Recap"],
                on_click=lambda r=row: _open_session_dialog(
                    source="live",
                    title=r["Name"] or r["Project"],
                    project=r["Project"],
                    session_id=r["Session ID"],
                    recap=r["Recap"],
                    recap_source=r["Recap Source"],
                    deletable=False,
                ),
            )

    _maybe_render_recap_dialog("live")


def render_transcripts_table() -> None:
    st.markdown(_ROW_CSS, unsafe_allow_html=True)

    df = _transcripts_dataframe()
    if df.empty:
        st.write("No Claude session transcripts found.")
        _maybe_render_recap_dialog("transcripts")
        return

    st.caption("Click a session to see what it was about.")
    live_ids = {session.session_id for session in load_sessions()}
    _render_table_header(_TRANSCRIPTS_COLUMNS, _TRANSCRIPTS_WIDTHS, key="table-header-transcripts")
    for row in df.to_dict("records"):
        _render_table_row(
            row,
            _TRANSCRIPTS_COLUMNS,
            _TRANSCRIPTS_WIDTHS,
            key=f"sessrow-transcripts-{row['Session ID']}",
            tooltip=row["Recap"],
            on_click=lambda r=row: _open_session_dialog(
                source="transcripts",
                title=r["Project"],
                project=r["Project"],
                session_id=r["Session ID"],
                recap=r["Recap"],
                recap_source=r["Recap Source"],
                deletable=r["Session ID"] not in live_ids,
            ),
        )

    _maybe_render_recap_dialog("transcripts")
