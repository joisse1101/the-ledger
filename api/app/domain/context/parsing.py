"""Parsing a transcript's JSON lines into turns, compactions and startup events."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

from app.repositories.db import scanner
from app.domain.context.models import Compaction, RawItem, StartupEvent, ToolUse, Turn


_HINT_KEYS = ("file_path", "path", "command", "pattern", "url", "query", "description", "prompt")
_HINT_MAX_CHARS = 80


def _str_list(value: Any) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _listing_items(text: str) -> tuple[RawItem, ...]:
    """Group `- name: description` lines into items; a line not starting with `- ` continues the previous one."""
    groups: list[list[str]] = []
    for line in text.split("\n"):
        if line.startswith("- ") or not groups:
            groups.append([line])
        else:
            groups[-1].append(line)
    items = []
    for group in groups:
        body = "\n".join(group)
        name = (body[2:] if body.startswith("- ") else body).split(":", 1)[0].strip()
        if name:
            items.append(RawItem(key=name, label=name, text=body))
    return tuple(items)


def _memory_items(files: Any) -> tuple[RawItem, ...]:
    items = []
    for file in files if isinstance(files, list) else []:
        if not isinstance(file, dict) or not isinstance(file.get("path"), str) or not isinstance(file.get("content"), str):
            continue
        path = file["path"]
        items.append(RawItem(key=path, label="/".join(re.split(r"[\\/]", path)[-2:]), text=file["content"]))
    return tuple(items)


def _mcp_items(attachment: dict) -> tuple[RawItem, ...]:
    blocks, names = _str_list(attachment.get("addedBlocks")), _str_list(attachment.get("addedNames"))
    items = []
    for index, block in enumerate(blocks):
        name = names[index] if len(names) == len(blocks) else block.split("\n", 1)[0].removeprefix("## ").strip()
        if name:
            items.append(RawItem(key=name, label=name, text=block))
    return tuple(items)


def _startup_events(attachment: Any, position: int) -> list[StartupEvent]:
    """The startup-content events carried by one transcript attachment, or [] for any other or malformed one."""
    if not isinstance(attachment, dict):
        return []
    kind = attachment.get("type")
    initial = attachment.get("isInitial") is True
    if kind == "instructions":
        event = StartupEvent(position, "memory", _memory_items(attachment.get("files")))
    elif kind == "skill_listing" and isinstance(attachment.get("content"), str):
        event = StartupEvent(position, "skills", _listing_items(attachment["content"]), replace=initial)
    elif kind == "agent_listing_delta":
        added = _listing_items("\n".join(_str_list(attachment.get("addedLines"))))
        event = StartupEvent(position, "agents", added, tuple(_str_list(attachment.get("removedTypes"))), replace=initial)
    elif kind == "mcp_instructions_delta":
        event = StartupEvent(position, "mcp", _mcp_items(attachment), tuple(_str_list(attachment.get("removedNames"))))
    else:
        return []
    return [event] if event.added or event.removed or event.replace else []


# ---------------------------------------------------------------- parsing


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _tool_hint(tool_input: Any) -> str:
    if not isinstance(tool_input, dict):
        return ""
    for key in _HINT_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            hint = " ".join(value.split())
            return hint if len(hint) <= _HINT_MAX_CHARS else hint[: _HINT_MAX_CHARS - 1] + "…"
    return ""


def _tool_uses(content: Any) -> list[ToolUse]:
    if not isinstance(content, list):
        return []
    return [
        ToolUse(name=block["name"], hint=_tool_hint(block.get("input")))
        for block in content
        if isinstance(block, dict) and block.get("type") == "tool_use" and isinstance(block.get("name"), str)
    ]


def scan(lines: Iterable[str]) -> tuple[list[Turn], list[Compaction], list[StartupEvent]]:
    turns: dict[str, Turn] = {}
    compactions: list[Compaction] = []
    events: list[StartupEvent] = []

    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue

        if entry.get("type") == "attachment":
            if not entry.get("isSidechain"):
                events.extend(_startup_events(entry.get("attachment"), len(turns)))
            continue

        if entry.get("type") == "system" and entry.get("subtype") == "compact_boundary":
            meta = entry.get("compactMetadata")
            meta = meta if isinstance(meta, dict) else {}
            pre_tokens = meta.get("preTokens")
            trigger = (meta.get("trigger") if isinstance(meta, dict) else None) or ""
            compactions.append(
                Compaction(
                    position=len(turns),
                    trigger=trigger,
                    pre_tokens=pre_tokens if isinstance(pre_tokens, int) else None,
                    timestamp=scanner.parse_iso_timestamp(entry.get("timestamp")),
                )
            )
            continue

        if entry.get("type") != "assistant" or entry.get("isSidechain"):
            continue
        message = entry.get("message")
        if not isinstance(message, dict) or message.get("model") == "<synthetic>":
            continue
        usage, message_id = message.get("usage"), message.get("id")
        if not isinstance(usage, dict) or not isinstance(message_id, str):
            continue

        turn = Turn(
            message_id=message_id,
            timestamp=scanner.parse_iso_timestamp(entry.get("timestamp")),
            new=_int(usage.get("input_tokens")),
            cache_read=_int(usage.get("cache_read_input_tokens")),
            cache_written=_int(usage.get("cache_creation_input_tokens")),
            output=_int(usage.get("output_tokens")),
        )
        if turn.context == 0:
            continue

        # A multi-block turn spans several lines that repeat the same id and usage, but each line
        # carries different content blocks - the last line's usage wins, the tools accumulate.
        previous = turns.get(message_id)
        turn.tools = (previous.tools if previous else []) + _tool_uses(message.get("content"))
        turns[message_id] = turn

    return list(turns.values()), compactions, events


def extract_turns(lines: Iterable[str]) -> list[Turn]:
    """Real main-thread responses in order: no sidechains, no `<synthetic>`/zero-usage placeholders."""
    return scan(lines)[0]
