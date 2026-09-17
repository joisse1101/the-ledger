"""SQLite-backed store for Claude Code project/transcript data.

Consolidates what used to be independent on-disk scans in claude_projects.py
and claude_transcripts.py (each with its own mtime cache) into one on-demand
refresh() that rescans ~/.claude.json and ~/.claude/projects/*/*.jsonl and
writes the result into a local SQLite database (.streamlit/ledger.db,
gitignored like theme_pref.json). claude_projects.py and claude_transcripts.py
now just query this database - refresh() is the only place that touches
those disk sources, triggered by the single refresh button in the nav bar
(app.py) instead of the two separate per-page refresh buttons it replaced.

claude_sessions.py is unaffected: its "Live" table polls
~/.claude/sessions/<pid>.json directly every 2s, a different, fast-changing
data source this refactor doesn't touch - though it benefits anyway, since
its call into claude_transcripts.load_transcripts() for project-name lookup
is now a cheap SQL query instead of a full jsonl rescan.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional, Generator


def db_path() -> Path:
    return Path(__file__).parent / ".streamlit" / "ledger.db"


def config_path() -> Path:
    return Path.home() / ".claude.json"


def projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def sanitize_project_path(path: str) -> str:
    """Convert a project directory path to Claude Code's on-disk project
    folder name under ~/.claude/projects/, e.g.
    "C:/Users/x/Repos/the-log" -> "C--Users-x-Repos-the-log". Every
    character that isn't alphanumeric becomes a dash."""
    return "".join(ch if ch.isalnum() else "-" for ch in path)


@contextmanager
def _connect() -> Generator[sqlite3.Connection, None, None]:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS projects (
            path TEXT PRIMARY KEY,
            trust_accepted INTEGER NOT NULL,
            last_session_id TEXT,
            last_version TEXT NOT NULL,
            last_cost REAL,
            last_start_time TEXT,
            last_duration_ms INTEGER,
            lines_added INTEGER,
            lines_removed INTEGER,
            mcp_servers TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS transcripts (
            session_id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            cwd TEXT NOT NULL,
            version TEXT NOT NULL,
            git_branch TEXT NOT NULL,
            started_at TEXT,
            updated_at TEXT,
            message_count INTEGER NOT NULL,
            cost REAL NOT NULL,
            project TEXT NOT NULL
        );
        """
    )


# ---------------------------------------------------------------------------
# Disk scanning - the only code in this app that reads ~/.claude.json and
# ~/.claude/projects/*/*.jsonl. Moved here from claude_projects.py /
# claude_transcripts.py, which now only query the database this produces.
# ---------------------------------------------------------------------------


def _parse_epoch_ms(value: Any) -> Optional[datetime]:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000)


def _scan_projects() -> list[dict[str, Any]]:
    path = config_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    rows = []
    for project_path, pdata in data.get("projects", {}).items():
        rows.append(
            {
                "path": project_path,
                "trust_accepted": bool(pdata.get("hasTrustDialogAccepted", False)),
                "last_session_id": pdata.get("lastSessionId"),
                "last_version": pdata.get("lastVersionBase", ""),
                "last_cost": pdata.get("lastCost"),
                "last_start_time": _parse_epoch_ms(pdata.get("lastStartTime")),
                "last_duration_ms": pdata.get("lastDuration"),
                "lines_added": pdata.get("lastLinesAdded"),
                "lines_removed": pdata.get("lastLinesRemoved"),
                "mcp_servers": sorted(pdata.get("mcpServers", {}).keys()),
            }
        )
    return rows


# model id -> (input $/1M tokens, output $/1M tokens)
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-fable-5-1": (10.00, 50.00),
    "claude-mythos-5-1": (10.00, 50.00),
    "claude-fable-5": (10.00, 50.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

# Prompt-cache multipliers, applied to a model's input price.
_CACHE_WRITE_5M_MULTIPLIER = 1.25
_CACHE_WRITE_1H_MULTIPLIER = 2.0
_CACHE_READ_MULTIPLIER = 0.1


def _message_cost(model: str, usage: dict[str, Any]) -> Optional[float]:
    """Cost of one API response given its `usage` block, or None for an
    unrecognized model (pricing unknown)."""
    pricing = _MODEL_PRICING.get(model)
    if pricing is None:
        return None
    input_price, output_price = pricing

    cache_creation = usage.get("cache_creation") or {}
    write_5m = cache_creation.get("ephemeral_5m_input_tokens")
    write_1h = cache_creation.get("ephemeral_1h_input_tokens")
    if write_5m is None and write_1h is None:
        # No per-tier breakdown; cache_creation_input_tokens defaults to the 5m tier.
        write_5m = usage.get("cache_creation_input_tokens", 0) or 0
        write_1h = 0

    return (
        (usage.get("input_tokens", 0) or 0) * input_price
        + (usage.get("output_tokens", 0) or 0) * output_price
        + (usage.get("cache_read_input_tokens", 0) or 0) * input_price * _CACHE_READ_MULTIPLIER
        + (write_5m or 0) * input_price * _CACHE_WRITE_5M_MULTIPLIER
        + (write_1h or 0) * input_price * _CACHE_WRITE_1H_MULTIPLIER
    ) / 1_000_000


def _parse_iso_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _scan_transcript_file(
    path: Path, project_by_folder: dict[str, str]
) -> Optional[dict[str, Any]]:
    session_id = path.stem
    cwd = ""
    version = ""
    git_branch = ""
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message_count = 0
    cost = 0.0
    seen_message_ids: set[str] = set()

    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                timestamp = _parse_iso_timestamp(entry.get("timestamp"))
                if timestamp is not None:
                    if started_at is None or timestamp < started_at:
                        started_at = timestamp
                    if updated_at is None or timestamp > updated_at:
                        updated_at = timestamp

                cwd = entry.get("cwd", cwd)
                version = entry.get("version", version)
                git_branch = entry.get("gitBranch", git_branch)
                session_id = entry.get("sessionId", session_id)

                if entry.get("type") in ("user", "assistant") and not entry.get("isMeta"):
                    message_count += 1

                message = entry.get("message")
                if entry.get("type") == "assistant" and isinstance(message, dict):
                    message_id = message.get("id")
                    # A multi-block assistant turn repeats the same usage on
                    # every line it spans - count each response's usage once.
                    if message_id and message_id not in seen_message_ids:
                        seen_message_ids.add(message_id)
                        usage = message.get("usage")
                        model = message.get("model")
                        if isinstance(usage, dict) and model:
                            turn_cost = _message_cost(model, usage)
                            if turn_cost is not None:
                                cost += turn_cost
    except OSError:
        return None

    # A session can `cd` partway through, leaving `cwd` pointing below the
    # real project root - trust the on-disk parent folder's project match
    # first, and only fall back to a cwd/folder-derived guess.
    project = project_by_folder.get(path.parent.name) or (
        Path(cwd).name if cwd else path.parent.name
    )

    return {
        "session_id": session_id,
        "path": path,
        "cwd": cwd,
        "version": version,
        "git_branch": git_branch,
        "started_at": started_at,
        "updated_at": updated_at,
        "message_count": message_count,
        "cost": cost,
        "project": project,
    }


def _scan_transcripts(project_by_folder: dict[str, str]) -> list[dict[str, Any]]:
    directory = projects_dir()
    if not directory.is_dir():
        return []
    rows = []
    for path in directory.glob("*/*.jsonl"):
        row = _scan_transcript_file(path, project_by_folder)
        if row is not None:
            rows.append(row)
    return rows


def refresh() -> datetime:
    """Rescan ~/.claude.json and ~/.claude/projects/*/*.jsonl from disk and
    replace the database's contents with what's found there. Returns the
    new refreshed-at timestamp."""
    project_rows = _scan_projects()
    project_by_folder = {
        sanitize_project_path(r["path"]): Path(r["path"]).name for r in project_rows
    }
    transcript_rows = _scan_transcripts(project_by_folder)
    now = datetime.now()

    with _connect() as conn:
        conn.execute("DELETE FROM projects")
        conn.executemany(
            """
            INSERT INTO projects (
                path, trust_accepted, last_session_id, last_version, last_cost,
                last_start_time, last_duration_ms, lines_added, lines_removed,
                mcp_servers
            ) VALUES (
                :path, :trust_accepted, :last_session_id, :last_version, :last_cost,
                :last_start_time, :last_duration_ms, :lines_added, :lines_removed,
                :mcp_servers
            )
            """,
            [
                {
                    **r,
                    "last_start_time": (
                        r["last_start_time"].isoformat() if r["last_start_time"] else None
                    ),
                    "mcp_servers": json.dumps(r["mcp_servers"]),
                }
                for r in project_rows
            ],
        )

        conn.execute("DELETE FROM transcripts")
        conn.executemany(
            """
            INSERT INTO transcripts (
                session_id, path, cwd, version, git_branch, started_at,
                updated_at, message_count, cost, project
            ) VALUES (
                :session_id, :path, :cwd, :version, :git_branch, :started_at,
                :updated_at, :message_count, :cost, :project
            )
            """,
            [
                {
                    **r,
                    "path": str(r["path"]),
                    "started_at": r["started_at"].isoformat() if r["started_at"] else None,
                    "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
                }
                for r in transcript_rows
            ],
        )

        conn.execute(
            """
            INSERT INTO meta (key, value) VALUES ('refreshed_at', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (now.isoformat(),),
        )

    return now


def refreshed_at() -> Optional[datetime]:
    """When the database was last refreshed from disk, or None if it never
    has been (e.g. a brand-new .streamlit/ledger.db)."""
    with _connect() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = 'refreshed_at'").fetchone()
    return datetime.fromisoformat(row["value"]) if row else None


def fetch_projects() -> list[sqlite3.Row]:
    """Every project row, newest-started first (NULLs last)."""
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM projects ORDER BY last_start_time IS NULL, last_start_time DESC"
        ).fetchall()


def fetch_transcripts() -> list[sqlite3.Row]:
    """Every transcript row, newest-updated first (NULLs last)."""
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM transcripts ORDER BY updated_at IS NULL, updated_at DESC"
        ).fetchall()


def delete_project_row(project_path: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM projects WHERE path = ?", (project_path,))


def transcript_paths_for_cwd(cwd: str) -> list[Path]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT path FROM transcripts WHERE cwd = ?", (cwd,)
        ).fetchall()
    return [Path(r["path"]) for r in rows]


def delete_transcript_rows_by_cwd(cwd: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM transcripts WHERE cwd = ?", (cwd,))


def transcript_path_for_session(session_id: str) -> Optional[Path]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT path FROM transcripts WHERE session_id = ?", (session_id,)
        ).fetchone()
    return Path(row["path"]) if row else None


def delete_transcript_row(session_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM transcripts WHERE session_id = ?", (session_id,))
