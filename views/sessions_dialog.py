"""Shared session-details and transcript-delete dialog."""

from datetime import datetime

import streamlit as st

from claude_transcripts import delete_transcript


def _open_session_dialog(*, source: str, heading: str, session_id: str, title: str,
                         last_message: str, first_prompt: str, started: datetime | None,
                         updated: datetime | None, deletable: bool) -> None:
    st.session_state.recap_dialog_info = {
        "source": source, "heading": heading, "session_id": session_id,
        "title": title, "last_message": last_message, "first_prompt": first_prompt,
        "started": started, "updated": updated, "deletable": deletable,
    }


def _dismiss_recap_dialog() -> None:
    st.session_state.recap_dialog_info = None
    st.session_state.pop("confirm_delete_session", None)


@st.dialog("Session details", on_dismiss=_dismiss_recap_dialog)
def _render_recap_dialog() -> None:
    info = st.session_state.get("recap_dialog_info")
    if not info:
        return

    st.markdown(f"**{info['heading']}**")
    if info["title"] or info["last_message"] or info["first_prompt"]:
        if info["title"]:
            st.caption("Session title")
            st.write(info["title"])
        if info["last_message"]:
            st.caption("Last message from Claude")
            st.write(info["last_message"])
        if info["first_prompt"]:
            st.caption("First prompt")
            st.write(info["first_prompt"])
    else:
        st.caption("No information available for this session yet.")

    if info["started"]:
        st.caption("Started")
        st.write(info["started"])
    if info["updated"]:
        st.caption("Last updated")
        st.write(info["updated"])

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
