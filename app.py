import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import config as st_config

from claude_projects import load_projects
from claude_sessions import load_sessions
from claude_transcripts import load_transcripts

_CONFIG_PATH = Path(__file__).parent / ".streamlit" / "config.toml"


def _persist_theme(theme: str) -> None:
    def _replace_base(match: re.Match) -> str:
        header, body = match.group(1), match.group(2)
        new_body = re.sub(r'(?m)^base\s*=\s*".*"$', f'base = "{theme}"', body, count=1)
        return f"{header}{new_body}"

    try:
        text = _CONFIG_PATH.read_text()
        new_text = re.sub(
            r'(?m)(^\[theme\]\s*\n)([\s\S]*?)(?=^\[|\Z)', _replace_base, text, count=1
        )
        if new_text != text:
            _CONFIG_PATH.write_text(new_text)
    except OSError:
        pass


def _sessions_dataframe() -> pd.DataFrame:
    sessions = load_sessions()
    return pd.DataFrame(
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


def _transcripts_dataframe() -> pd.DataFrame:
    transcripts = load_transcripts()
    return pd.DataFrame(
        [
            {
                "Project": t.project,
                "Session ID": t.session_id,
                "Started": t.started_at,
                "Last Updated": t.updated_at,
                "Messages": t.message_count,
                "Est. Cost ($)": t.cost,
                "Version": t.version,
                "Git Branch": t.git_branch,
            }
            for t in transcripts
        ]
    )


def _projects_dataframe() -> pd.DataFrame:
    projects = load_projects()
    return pd.DataFrame(
        [
            {
                "Name": p.name,
                "Path": p.path,
                "Trusted": p.trust_accepted,
                "Last Session": p.last_session_id,
                "Version": p.last_version,
                "Last Cost ($)": p.last_cost,
                "Last Started": p.last_start_time,
                "Lines +/-": (
                    f"+{p.lines_added}/-{p.lines_removed}"
                    if p.lines_added is not None or p.lines_removed is not None
                    else None
                ),
                "MCP Servers": ", ".join(p.mcp_servers) if p.mcp_servers else None,
            }
            for p in projects
        ]
    )


def render_projects_table() -> None:
    if "projects_df" not in st.session_state:
        st.session_state.projects_df = _projects_dataframe()
        st.session_state.projects_refreshed_at = datetime.now()

    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("⟳"):
            st.session_state.projects_df = _projects_dataframe()
            st.session_state.projects_refreshed_at = datetime.now()
        st.caption(f"Last refreshed: {st.session_state.projects_refreshed_at:%H:%M:%S}")

    df = st.session_state.projects_df
    if df.empty:
        st.write("No Claude projects found.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_transcripts_table() -> None:
    if "transcripts_df" not in st.session_state:
        st.session_state.transcripts_df = _transcripts_dataframe()
        st.session_state.transcripts_refreshed_at = datetime.now()

    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("⟳", key="transcripts_refresh"):
            st.session_state.transcripts_df = _transcripts_dataframe()
            st.session_state.transcripts_refreshed_at = datetime.now()
        st.caption(
            f"Last refreshed: {st.session_state.transcripts_refreshed_at:%H:%M:%S}"
        )

    df = st.session_state.transcripts_df
    if df.empty:
        st.write("No Claude session transcripts found.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


@st.fragment(run_every="2s")
def render_sessions_table() -> None:
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
        st.dataframe(df, use_container_width=True, hide_index=True)


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
        st.divider()
        dark_mode = st.toggle(
            "Dark mode",
            value=st_config.get_option("theme.base") == "dark",
            key="dark_mode",
        )

    desired_theme = "dark" if dark_mode else "light"
    if st_config.get_option("theme.base") != desired_theme:
        st_config.set_option("theme.base", desired_theme)
        _persist_theme(desired_theme)
        st.rerun()

    if st.session_state.page == "sessions":
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
