"""Disk scanning: the only code that reads ~/.claude.json and ~/.claude/projects/*/*.jsonl."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import json

from app.repositories.db import paths


# ---------------------------------------------------------------------------
# Disk scanning - the only code in this app that reads ~/.claude.json and
# ~/.claude/projects/*/*.jsonl.
# ---------------------------------------------------------------------------


def _parse_epoch_ms(value: Any) -> Optional[datetime]:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000)


def scan_projects() -> list[dict[str, Any]]:
    path = paths.config_path()
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
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5-5": (2.00, 10.00),
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


def parse_iso_timestamp(value: Any) -> Optional[datetime]:
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


# OpenSpec is driven by `/opsx:*` slash commands, or by the `openspec-*` / `opsx:*` skills (which the
# model can also call itself through the Skill tool).
_OPENSPEC_COMMAND_RE = re.compile(r"<command-name>\s*/(?:opsx:|openspec-)")


def _calls_openspec_skill(content: Any) -> bool:
    if not isinstance(content, list):
        return False
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Skill":
            skill = (block.get("input") or {}).get("skill")
            if isinstance(skill, str) and skill.startswith(("openspec-", "opsx:")):
                return True
    return False


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
    `parsing.scan`, so a finished session's stored value is the same number the
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
    unpriced_models: set[str] = set()
    model_turns: Counter[str] = Counter()
    used_openspec = False
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

                timestamp = parse_iso_timestamp(entry.get("timestamp"))
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
                        if model and model != "<synthetic>" and not entry.get("isSidechain"):
                            model_turns[model] += 1
                        if isinstance(usage, dict) and model:
                            turn_cost = _message_cost(model, usage)
                            if turn_cost is not None:
                                cost += turn_cost
                            else:
                                unpriced_models.add(model)

                    text = _extract_text(message.get("content"))
                    if text:
                        last_assistant_text = text
                    if not used_openspec and _calls_openspec_skill(message.get("content")):
                        used_openspec = True

                if (
                    entry.get("type") == "user"
                    and not used_openspec
                    and isinstance(message, dict)
                ):
                    # A slash command is recorded as a user line wrapping `<command-name>`
                    # (isMeta is false on it).
                    command_text = _extract_text(message.get("content"))
                    if command_text and _OPENSPEC_COMMAND_RE.search(command_text):
                        used_openspec = True

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
        cost_state_flagged = False
    else:
        cost_source = "estimated"
        # True only when a cost-state line was found and it flagged the gap itself (as opposed
        # to no cost-state line existing at all - a session still in progress, or one from a
        # build too old to write one) - lets the frontend say which of those two applies.
        cost_state_flagged = cost_state_total is not None and cost_state_has_unknown

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
        "unpriced_models": sorted(unpriced_models),
        "cost_state_flagged": cost_state_flagged,
        # The model with the most main-thread responses; ties go to the one seen first.
        "model": model_turns.most_common(1)[0][0] if model_turns else "",
        "used_openspec": used_openspec,
        "context": context,
        "project": project,
        "title": title,
        "last_message": last_message,
        "first_prompt": first_prompt,
    }


def scan_transcripts(project_by_folder: dict[str, str]) -> list[dict[str, Any]]:
    directory = paths.projects_dir()
    if not directory.is_dir():
        return []
    rows = []
    for path in directory.glob("*/*.jsonl"):
        row = _scan_transcript_file(path, project_by_folder)
        if row is not None:
            rows.append(row)
    return rows
