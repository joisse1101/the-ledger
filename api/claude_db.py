"""SQLite-backed store for Claude Code project/transcript data.

refresh() is the only place that reads ~/.claude.json and
~/.claude/projects/*/*.jsonl from disk; everything else (claude_projects,
claude_transcripts) just queries the SQLite snapshot it writes. Live-session
polling (claude_sessions) reads its own registry and doesn't go through here.
"""

from __future__ import annotations

import atexit
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Generator, Optional


_BUSY_TIMEOUT_MS = 10_000


def db_path() -> Path:
    return Path(__file__).parent / ".ledger" / "ledger.db"


def history_db_path() -> Path:
    return Path(__file__).parent / ".history" / "history.db"


def config_path() -> Path:
    return Path.home() / ".claude.json"


def projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def sanitize_project_path(path: str) -> str:
    """Project dir path -> its ~/.claude/projects/ folder name.

    - Every non-alphanumeric character becomes a dash, e.g.
      "C:/Users/x/Repos/the-log" -> "C--Users-x-Repos-the-log".
    """
    return "".join(ch if ch.isalnum() else "-" for ch in path)


@contextmanager
def _connect_to(
    path: Path, ensure_schema: Callable[[sqlite3.Connection], None]
) -> Generator[sqlite3.Connection, None, None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=_BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    try:
        # WAL lets the API's readers keep reading while a writer commits its
        # own table replacement; the timeout makes the rare remaining collision wait.
        conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA journal_mode = WAL")
        ensure_schema(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


@contextmanager
def _connect() -> Generator[sqlite3.Connection, None, None]:
    with _connect_to(db_path(), _ensure_schema) as conn:
        yield conn


@contextmanager
def _connect_history() -> Generator[sqlite3.Connection, None, None]:
    with _connect_to(history_db_path(), _ensure_history_schema) as conn:
        yield conn


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
        """
    )
    _ensure_history_schema(conn)


def _ensure_history_schema(conn: sqlite3.Connection) -> None:
    """`transcripts` table shape shared by ledger.db (disposable) and history.db (durable)."""
    conn.executescript(
        """
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
            cost_source TEXT NOT NULL DEFAULT 'estimated',
            context INTEGER,
            project TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            last_message TEXT NOT NULL DEFAULT '',
            first_prompt TEXT NOT NULL DEFAULT ''
        );
        """
    )
    # history.db is never recreated, so a pre-existing file's table predates this
    # column - add it in place. ledger.db's CREATE TABLE above already includes
    # it (that table is dropped and rebuilt every start), so this is a no-op
    # there beyond the harmless "duplicate column" error being swallowed.
    try:
        conn.execute(
            "ALTER TABLE transcripts ADD COLUMN cost_source TEXT NOT NULL DEFAULT 'estimated'"
        )
    except sqlite3.OperationalError:
        pass


# ---------------------------------------------------------------------------
# Disk scanning - the only code in this app that reads ~/.claude.json and
# ~/.claude/projects/*/*.jsonl.
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
    for project_path, project_info in data.get("projects", {}).items():
        rows.append(
            {
                "path": project_path,
                "trust_accepted": bool(project_info.get("hasTrustDialogAccepted", False)),
                "last_session_id": project_info.get("lastSessionId"),
                "last_version": project_info.get("lastVersionBase", ""),
                "last_cost": project_info.get("lastCost"),
                "last_start_time": _parse_epoch_ms(project_info.get("lastStartTime")),
                "last_duration_ms": project_info.get("lastDuration"),
                "lines_added": project_info.get("lastLinesAdded"),
                "lines_removed": project_info.get("lastLinesRemoved"),
                "mcp_servers": sorted(project_info.get("mcpServers", {}).keys()),
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
    """Dollar cost of one API response, or None if the model has no pricing entry."""
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


# Wrapper tags Claude Code (or this app's own injected context) inserts
# around a user turn - e.g. a bare slash command's expansion, or the
# system-reminder blob repeated at the top of most turns. None of these are
# something the user actually typed, so they're stripped before a message is
# considered as a "first prompt" recap fallback.
_WRAPPER_TAG_RE = re.compile(
    r"<(system-reminder|command-name|command-message|command-args|"
    r"local-command-stdout|local-command-caveat)>.*?</\1>",
    re.DOTALL,
)


def _extract_text(content: Any) -> Optional[str]:
    """Plain text from a message's `content` (a string, or a list of blocks) - text
    blocks only, tool_use/tool_result/image blocks are ignored."""
    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        joined = "\n\n".join(part for part in parts if part)
        return joined.strip() or None
    return None


def _clean_wrapper_tags(text: str) -> Optional[str]:
    cleaned = _WRAPPER_TAG_RE.sub("", text).strip()
    return cleaned or None


_FENCED_CODE_RE = re.compile(
    r"^[ \t]{0,3}(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^[ \t]{0,3}(?P=fence)[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
_INLINE_CODE_RE = re.compile(
    r"(?P<ticks>`+)(?!`)(?:(?!(?P=ticks)).)*?(?P=ticks)"
)
_BOLD_RE = re.compile(r"(?<![\\\w])(\*\*|__)(?=\S)(.*?)(?<=\S)\1(?!\w)")
_ASTERISK_ITALIC_RE = re.compile(r"(?<![\\\w*])\*(?=\S)(.*?)(?<=\S)\*(?![\w*])")
_UNDERSCORE_ITALIC_RE = re.compile(r"(?<![\\\w_])_(?=\S)(.*?)(?<=\S)_(?![\w_])")
_ATX_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}(?:[ \t]+|$)")
_CLOSING_HEADING_HASHES_RE = re.compile(r"(?:[ \t]+#+)[ \t]*$")
_SETEXT_HEADING_RE = re.compile(r"^[ \t]{0,3}(?:=+|-+)[ \t]*$")


def _strip_prose_markdown(text: str) -> str:
    """Remove presentation-only Markdown from text outside code spans."""
    lines = text.splitlines()
    stripped_lines: list[str] = []
    for index, line in enumerate(lines):
        # Setext headings are a text line followed by === or ---.  Keep the
        # text itself, but drop its underline so it cannot render as a header.
        if (
            _SETEXT_HEADING_RE.match(line)
            and index > 0
            and lines[index - 1].strip()
        ):
            continue

        line = _ATX_HEADING_RE.sub("", line)
        line = _CLOSING_HEADING_HASHES_RE.sub("", line)
        stripped_lines.append(line)

    prose = "\n".join(stripped_lines)
    # Re-run each pattern so nested emphasis such as ***important*** is fully
    # unwrapped.  Delimiter checks intentionally leave ordinary symbols (for
    # example multiplication operators and identifier underscores) untouched.
    previous = None
    while prose != previous:
        previous = prose
        prose = _BOLD_RE.sub(r"\2", prose)
        prose = _ASTERISK_ITALIC_RE.sub(r"\1", prose)
        prose = _UNDERSCORE_ITALIC_RE.sub(r"\1", prose)
    return prose


def _normalize_snippet(text: str, max_len: int = 600) -> str:
    """Create a compact Markdown snippet without prose emphasis or headings.

    Code is protected before prose is normalized, so its delimiters, whitespace,
    symbols, and emoji are retained exactly as authored.
    """
    code_parts: list[tuple[str, bool]] = []

    def protect_fenced_code(match: re.Match[str]) -> str:
        code_parts.append((match.group(0), True))
        return f" \ue000{len(code_parts) - 1}\ue001 "

    protected = _FENCED_CODE_RE.sub(protect_fenced_code, text)

    def protect_inline_code(match: re.Match[str]) -> str:
        code_parts.append((match.group(0), False))
        return f"\ue000{len(code_parts) - 1}\ue001"

    protected = _INLINE_CODE_RE.sub(protect_inline_code, protected)
    collapsed = " ".join(_strip_prose_markdown(protected).split())

    for index, (code, is_fenced) in enumerate(code_parts):
        placeholder = f"\ue000{index}\ue001"
        replacement = f"\n\n{code}\n\n" if is_fenced else code
        collapsed = collapsed.replace(placeholder, replacement)

    normalized = re.sub(r" *\n\n *", "\n\n", collapsed)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    if len(normalized) > max_len:
        return normalized[: max_len].rstrip() + "…"
    return normalized


def _context_tokens(entry: dict[str, Any]) -> Optional[int]:
    """Context size at one assistant line: `input + cache_read + cache_creation` tokens.

    None for lines that aren't a real main-thread response - sidechains, `<synthetic>`
    API-error placeholders, missing usage/id, or zero usage. Must stay in step with
    `claude_context._scan`, so a finished session's stored value is the same number the
    Live table's gauge showed for it.
    """
    message = entry.get("message")
    if entry.get("type") != "assistant" or entry.get("isSidechain") or not isinstance(message, dict):
        return None
    usage = message.get("usage")
    if (
        message.get("model") == "<synthetic>"
        or not isinstance(usage, dict)
        or not isinstance(message.get("id"), str)
    ):
        return None
    total = sum(
        value if isinstance(value, int) and not isinstance(value, bool) else 0
        for value in (
            usage.get("input_tokens"),
            usage.get("cache_read_input_tokens"),
            usage.get("cache_creation_input_tokens"),
        )
    )
    return total or None


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
    cost_state_total: Optional[float] = None
    cost_state_has_unknown = False
    context: Optional[int] = None
    seen_message_ids: set[str] = set()
    ai_title: Optional[str] = None
    last_assistant_text: Optional[str] = None
    first_user_text: Optional[str] = None

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

                if entry.get("type") == "ai-title":
                    ai_title = entry.get("aiTitle") or ai_title

                if entry.get("type") == "cost-state":
                    # No timestamp on these lines; the file is append-ordered, so the
                    # last one encountered during this single pass is the most recent.
                    total = entry.get("totalCostUSD")
                    if isinstance(total, (int, float)):
                        cost_state_total = float(total)
                        cost_state_has_unknown = bool(entry.get("hasUnknownModelCost", False))

                turn_context = _context_tokens(entry)
                if turn_context is not None:
                    context = turn_context

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

                    text = _extract_text(message.get("content"))
                    if text:
                        last_assistant_text = text

                if (
                    entry.get("type") == "user"
                    and not entry.get("isMeta")
                    and first_user_text is None
                    and isinstance(message, dict)
                ):
                    text = _extract_text(message.get("content"))
                    if text:
                        cleaned = _clean_wrapper_tags(text)
                        if cleaned:
                            first_user_text = cleaned
    except OSError:
        return None

    # Prefer Claude Code's own cumulative, Anthropic-priced, subagent-inclusive
    # tracker over this file's per-message recompute - the latter is kept only
    # as a fallback estimate for a transcript with no clean cost-state line
    # (still in progress, predates cost-state, or flags an unpriced model itself).
    if cost_state_total is not None and not cost_state_has_unknown:
        cost, cost_source = cost_state_total, "exact"
    else:
        cost_source = "estimated"

    # Claude Code's own auto-generated session title, the last thing the
    # assistant said (a recap, a wrap-up summary, a follow-up question -
    # whatever it naturally is), and the first thing the user actually
    # typed - stored separately rather than collapsed into one fallback
    # chain, so callers can show whichever of these fit their context.
    title = _normalize_snippet(ai_title) if ai_title else ""
    last_message = _normalize_snippet(last_assistant_text) if last_assistant_text else ""
    first_prompt = _normalize_snippet(first_user_text) if first_user_text else ""

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
        "cost_source": cost_source,
        "context": context,
        "project": project,
        "title": title,
        "last_message": last_message,
        "first_prompt": first_prompt,
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


def _serialize_transcript_row(row: dict[str, Any]) -> dict[str, Any]:
    """A `_scan_transcripts()`-shaped row (Path/datetime fields) -> one ready for SQLite binding."""
    return {
        **row,
        "path": str(row["path"]),
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


_TRANSCRIPT_UPSERT_SQL = """
    INSERT INTO transcripts (
        session_id, path, cwd, version, git_branch, started_at,
        updated_at, message_count, cost, cost_source, context, project, title,
        last_message, first_prompt
    ) VALUES (
        :session_id, :path, :cwd, :version, :git_branch, :started_at,
        :updated_at, :message_count, :cost, :cost_source, :context, :project, :title,
        :last_message, :first_prompt
    )
    ON CONFLICT(session_id) DO UPDATE SET
        path = excluded.path,
        cwd = excluded.cwd,
        version = excluded.version,
        git_branch = excluded.git_branch,
        started_at = excluded.started_at,
        updated_at = excluded.updated_at,
        message_count = excluded.message_count,
        cost = excluded.cost,
        cost_source = excluded.cost_source,
        context = excluded.context,
        project = excluded.project,
        title = excluded.title,
        last_message = excluded.last_message,
        first_prompt = excluded.first_prompt
"""


def upsert_history_transcripts(rows: list[dict[str, Any]]) -> None:
    """Insert or update `history.db` transcript rows, keyed by `session_id`.

    `rows` is `_scan_transcripts()`-shaped (Path/datetime fields, one dict per transcript).
    A row whose `session_id` already exists is overwritten in place rather than duplicated,
    so re-running a backup against a still-growing session never creates a second row for it.
    """
    if not rows:
        return
    with _connect_history() as conn:
        conn.executemany(_TRANSCRIPT_UPSERT_SQL, [_serialize_transcript_row(r) for r in rows])


def fetch_history_transcripts() -> list[sqlite3.Row]:
    """Every transcript row ever backed up to `history.db`, including ones since pruned from disk."""
    with _connect_history() as conn:
        return conn.execute("SELECT * FROM transcripts").fetchall()


def refresh() -> datetime:
    """Rescan disk and replace the database's contents; returns the new refreshed-at timestamp."""
    project_rows = _scan_projects()
    project_by_folder = {
        sanitize_project_path(p["path"]): Path(p["path"]).name for p in project_rows
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
                    **p,
                    "last_start_time": (
                        p["last_start_time"].isoformat() if p["last_start_time"] else None
                    ),
                    "mcp_servers": json.dumps(p["mcp_servers"]),
                }
                for p in project_rows
            ],
        )

        conn.execute("DELETE FROM transcripts")
        conn.executemany(
            """
            INSERT INTO transcripts (
                session_id, path, cwd, version, git_branch, started_at,
                updated_at, message_count, cost, cost_source, context, project, title,
                last_message, first_prompt
            ) VALUES (
                :session_id, :path, :cwd, :version, :git_branch, :started_at,
                :updated_at, :message_count, :cost, :cost_source, :context, :project, :title,
                :last_message, :first_prompt
            )
            """,
            [_serialize_transcript_row(t) for t in transcript_rows],
        )

        conn.execute(
            """
            INSERT INTO meta (key, value) VALUES ('refreshed_at', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (now.isoformat(),),
        )

    return now


_started = False


def _remove_db_files(path: Path) -> None:
    """Delete the database and its WAL side files (best effort)."""
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(f"{path}{suffix}").unlink(missing_ok=True)
        except OSError:
            pass


def startup() -> None:
    """Wipe any on-disk snapshot left over from a previous run and rebuild it fresh.

    - Database is a derived cache, never a source of truth
    - Registers a best-effort cleanup of the same files (including the WAL's
      `-wal`/`-shm` side files) on process exit
    """
    global _started
    if _started:
        return
    _started = True
    path = db_path()
    _remove_db_files(path)
    refresh()
    atexit.register(_remove_db_files, path)


def refreshed_at() -> Optional[datetime]:
    """When the database was last refreshed, or None for a brand-new db."""
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
    """Every transcript row, live `ledger.db` rows merged with `history.db`'s durable rows by
    `session_id` (the live row wins whenever a session exists in both - it's the fresher scan),
    newest-updated first (NULLs last)."""
    with _connect() as conn:
        live_rows = conn.execute("SELECT * FROM transcripts").fetchall()
    history_rows = fetch_history_transcripts()

    merged: dict[str, sqlite3.Row] = {row["session_id"]: row for row in history_rows}
    merged.update({row["session_id"]: row for row in live_rows})

    # Empty string sorts before any ISO timestamp, so `reverse=True` puts NULLs
    # (mapped to "") last while still ordering real timestamps newest-first.
    return sorted(merged.values(), key=lambda row: row["updated_at"] or "", reverse=True)


def delete_project_row(project_path: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM projects WHERE path = ?", (project_path,))


def transcript_paths_for_project(project_path: str) -> list[Path]:
    """Transcript file paths filed under `project_path`'s own `~/.claude/projects/` folder.

    Matched by that on-disk folder name (`sanitize_project_path(project_path)`) rather than
    each transcript's own recorded `cwd` - a session can `cd` partway through and leave `cwd`
    pointing below the project root, but the folder a transcript is filed under never changes.
    """
    folder = sanitize_project_path(project_path)
    with _connect() as conn:
        rows = conn.execute("SELECT DISTINCT path FROM transcripts").fetchall()
    return [Path(row["path"]) for row in rows if Path(row["path"]).parent.name == folder]


def _delete_transcript_rows_by_project_in(
    connect: Callable[[], Any], folder: str
) -> None:
    with connect() as conn:
        rows = conn.execute("SELECT session_id, path FROM transcripts").fetchall()
        session_ids = [row["session_id"] for row in rows if Path(row["path"]).parent.name == folder]
        if session_ids:
            conn.executemany(
                "DELETE FROM transcripts WHERE session_id = ?",
                [(sid,) for sid in session_ids],
            )


def delete_transcript_rows_by_project(project_path: str) -> None:
    """Remove a project's transcript rows from both `ledger.db` and `history.db`.

    Matched by the same on-disk folder name `transcript_paths_for_project` uses, since a
    `history.db` row (a session already pruned from disk) carries the same `path` shape.
    """
    folder = sanitize_project_path(project_path)
    _delete_transcript_rows_by_project_in(_connect, folder)
    _delete_transcript_rows_by_project_in(_connect_history, folder)


def transcript_path_for_session(session_id: str) -> Optional[Path]:
    """A session's transcript path from `ledger.db`, falling back to `history.db` when the
    session is no longer live (e.g. already pruned from disk) - so callers checking whether a
    session is known at all (the delete route's 404 check) recognize a history-only session too.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT path FROM transcripts WHERE session_id = ?", (session_id,)
        ).fetchone()
    if row is not None:
        return Path(row["path"])
    with _connect_history() as conn:
        row = conn.execute(
            "SELECT path FROM transcripts WHERE session_id = ?", (session_id,)
        ).fetchone()
    return Path(row["path"]) if row else None


def delete_transcript_row(session_id: str) -> None:
    """Remove one session's row from whichever of `ledger.db`/`history.db` has it."""
    with _connect() as conn:
        conn.execute("DELETE FROM transcripts WHERE session_id = ?", (session_id,))
    with _connect_history() as conn:
        conn.execute("DELETE FROM transcripts WHERE session_id = ?", (session_id,))
