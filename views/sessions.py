"""Sessions page composition."""

import streamlit as st

from views.sessions_live import render_sessions_table
from views.sessions_transcripts import render_transcripts_table


def render_sessions_page() -> None:
    """Render the live-session and transcript sections of the Sessions page."""
    st.header("Sessions")
    st.subheader("Live")
    render_sessions_table()

    st.subheader("All")
    render_transcripts_table()
