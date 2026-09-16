"""Parser for Claude Code's on-disk session transcripts
(~/.claude/projects/<sanitized-cwd>/<session-id>.jsonl).

Unlike the live session registry, this covers every session that has ever
run, including ones whose process has since exited.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


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


@dataclass
class ClaudeTranscript:
    session_id: str
    path: Path
    cwd: str
    version: str
    git_branch: str
    started_at: Optional[datetime]
    updated_at: Optional[datetime]
    message_count: int
    cost: float

    @property
    def project(self) -> str:
        return Path(self.cwd).name if self.cwd else self.path.parent.name


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_transcript_file(path: Path) -> Optional[ClaudeTranscript]:
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

                timestamp = _parse_timestamp(entry.get("timestamp"))
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

    return ClaudeTranscript(
        session_id=session_id,
        path=path,
        cwd=cwd,
        version=version,
        git_branch=git_branch,
        started_at=started_at,
        updated_at=updated_at,
        message_count=message_count,
        cost=cost,
    )


# path -> (mtime at last parse, parsed transcript)
_cache: dict[Path, tuple[float, ClaudeTranscript]] = {}


def load_transcripts(directory: Optional[Path] = None) -> list[ClaudeTranscript]:
    """Read and parse every session transcript, newest-updated first.

    Scans every *.jsonl file under every project folder in
    ~/.claude/projects/. Files unchanged since the last call (by mtime)
    are served from an in-memory cache instead of being re-read/re-parsed.
    """
    directory = directory or projects_dir()
    if not directory.is_dir():
        _cache.clear()
        return []

    seen_paths: set[Path] = set()
    transcripts: list[ClaudeTranscript] = []

    for path in directory.glob("*/*.jsonl"):
        seen_paths.add(path)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue

        cached = _cache.get(path)
        if cached is not None and cached[0] == mtime:
            transcripts.append(cached[1])
            continue

        transcript = _parse_transcript_file(path)
        if transcript is None:
            _cache.pop(path, None)
            continue

        _cache[path] = (mtime, transcript)
        transcripts.append(transcript)

    for stale_path in _cache.keys() - seen_paths:
        del _cache[stale_path]

    transcripts.sort(
        key=lambda t: t.updated_at or datetime.min,
        reverse=True,
    )
    return transcripts


def delete_project_transcripts(cwd: str, directory: Optional[Path] = None) -> int:
    """Delete the on-disk transcript directory/directories for a given cwd.

    Matches transcripts by their recorded `cwd` field rather than
    re-deriving Claude Code's directory-name sanitization, so it stays
    correct even if that scheme changes. Returns the number of
    directories removed.
    """
    transcripts = load_transcripts(directory)
    dirs = {t.path.parent for t in transcripts if t.cwd == cwd}

    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)
        for cached_path in [p for p in _cache if p.parent == d]:
            del _cache[cached_path]

    return len(dirs)


def delete_transcript(session_id: str, directory: Optional[Path] = None) -> bool:
    """Delete a single session's transcript file by session_id.

    Returns True if the transcript was found and deleted.
    """
    for transcript in load_transcripts(directory):
        if transcript.session_id != session_id:
            continue
        try:
            transcript.path.unlink()
        except OSError:
            return False
        _cache.pop(transcript.path, None)
        return True
    return False
