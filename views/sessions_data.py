"""Dataframe construction and filtering for the Sessions page."""

from typing import Sequence

import pandas as pd

from claude_sessions import load_sessions
from claude_transcripts import load_transcripts


def _sessions_dataframe() -> pd.DataFrame:
    """The Live table's rows, one per running Claude Code session."""
    sessions = load_sessions()
    return pd.DataFrame(
        [
            {"Name": s.name, "Project": s.project, "Title": s.title,
             "Status": s.status, "Kind": s.kind, "PID": s.pid,
             "Started": s.started_at, "Last Updated": s.updated_at,
             "Session ID": s.session_id, "Last Message": s.last_message,
             "First Prompt": s.first_prompt}
            for s in sessions
        ]
    )


def _transcripts_dataframe() -> pd.DataFrame:
    """The All table's rows, one per session transcript ever recorded."""
    transcripts = load_transcripts()
    return pd.DataFrame(
        [
            {"Project": t.project, "Title": t.title, "Session ID": t.session_id,
             "Started": t.started_at, "Last Updated": t.updated_at,
             "Messages": t.message_count, "Est. Cost ($)": t.cost,
             "Version": t.version, "Git Branch": t.git_branch,
             "Last Message": t.last_message, "First Prompt": t.first_prompt}
            for t in transcripts
        ]
    )


def _categorical_options(df: pd.DataFrame, column: str) -> list[str]:
    """Distinct, non-blank values of `column`, for a filter multiselect's options."""
    return sorted({str(value) for value in df[column].dropna() if str(value).strip()})


def _sort_transcripts_dataframe(df: pd.DataFrame, sort_column: str, ascending: bool) -> pd.DataFrame:
    """Stable sort by any column, pushing missing values to the end either way."""
    if df.empty or sort_column not in df.columns:
        return df
    return df.sort_values(by=sort_column, ascending=ascending, kind="mergesort", na_position="last")


def _filter_transcripts_dataframe(
    df: pd.DataFrame, *, search: str = "", projects: Sequence[str] = (),
    versions: Sequence[str] = (), branches: Sequence[str] = (),
) -> pd.DataFrame:
    """Narrow the All table to rows matching all selected filters."""
    if search:
        df = df[df["Session ID"].str.contains(search, case=False, na=False, regex=False)]
    if projects:
        df = df[df["Project"].isin(projects)]
    if versions:
        df = df[df["Version"].isin(versions)]
    if branches:
        df = df[df["Git Branch"].isin(branches)]
    return df
