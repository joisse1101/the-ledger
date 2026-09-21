"""Shared clickable-table presentation helpers for the Sessions page."""

from datetime import datetime
from typing import Sequence

import pandas as pd
import streamlit as st


_ROW_CSS = """
<style>
[class*="st-key-sessrow-"] { position: relative; border-bottom: 1px solid rgba(128, 128, 128, 0.18); padding: 0.35rem 0; }
[class*="st-key-sessrow-"]:hover { background-color: rgba(128, 128, 128, 0.12); }
[class*="st-key-sessrow-"] [data-testid="stElementContainer"]:has([data-testid="stButton"]), [class*="st-key-sessrow-"] [data-testid="stButton"], [class*="st-key-sessrow-"] [data-testid="stButton"] > div { position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; }
[class*="st-key-sessrow-"] [data-testid="stButton"] button { position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; min-height: 100% !important; opacity: 0; cursor: pointer; border: none !important; padding: 0 !important; margin: 0 !important; }
[data-testid="stVerticalBlock"][class*="st-key-table-header-"] { padding-bottom: 0.35rem; margin-bottom: 0.1rem; font-weight: 600; display: flex; height: 2rem; max-height: 2rem; }
[class*="st-key-table-header-"] [data-testid="stButton"], [class*="st-key-table-header-"] [data-testid="stButton"] > button { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important; font-weight: 600 !important; text-align: left !important; width: 100% !important; color: inherit !important; }
[class*="st-key-table-header-"] [data-testid="stButton"] > button:hover, [class*="st-key-table-header-"] [data-testid="stButton"] > button:focus { background: transparent !important; border: none !important; box-shadow: none !important; text-decoration: none !important; color: inherit !important; }
</style>
"""


def _format_cell(value: pd.Timestamp | datetime | float | str | None) -> str:
    if pd.isna(value) or (type(value) == str and value.strip() == ""):
        return "--"
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _tooltip_text(row: dict) -> str:
    session_id = row.get("Session ID")
    msg_title = "Last Message" if row.get("Last Message") else "First Prompt" if row.get("First Prompt") else ""
    msg = f"{row.get('Last Message') or row.get('First Prompt') or ''}"
    msg = msg[:200].strip() + ("..." if len(msg) > 200 else "")
    final_msg = f"{msg_title}:  \n{msg}" if msg else ""
    prefix = f"[{row.get('Title')}] " if row.get("Title") else ""
    return f"{prefix}{session_id}" + (f"  \n  \n{final_msg}" if final_msg else "")


def _render_table_header(labels: Sequence[str], widths: Sequence[int], *, key: str) -> None:
    with st.container(key=key):
        for col, label in zip(st.columns(widths), labels):
            col.markdown(f"**{label}**")


def _render_sortable_table_header(labels: Sequence[str], widths: Sequence[int], *, key: str, sort_state_key: str) -> None:
    sort_column, ascending = st.session_state[sort_state_key]
    with st.container(key=key):
        for col, label in zip(st.columns(widths), labels):
            arrow = " ▲" if label == sort_column and ascending else " ▼" if label == sort_column else ""
            if col.button(f"{label}{arrow}", key=f"{key}-sort-{label}", use_container_width=True):
                st.session_state[sort_state_key] = (label, not ascending) if label == sort_column else (label, True)
                st.rerun()


def _render_table_row(row: dict, columns: Sequence[str], widths: Sequence[int], *, key: str, tooltip: str, on_click) -> None:
    with st.container(key=key):
        for col, name in zip(st.columns(widths, vertical_alignment="center"), columns):
            col.write(_format_cell(row[name]))
        if st.button("", key=f"{key}-btn", help=tooltip or None, use_container_width=True):
            on_click()
