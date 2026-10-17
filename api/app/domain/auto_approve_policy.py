"""Which pending prompts auto-approve may answer on its own.

Pure and I/O free. A prompt is auto-approvable when it is a plain permission dialog: not a question
for the user (`AskUserQuestion`), not a plan to approve (`ExitPlanMode`), and - for a shell tool - not
a command that matches a known-dangerous pattern. The pattern list is a best-effort guard, not a
security boundary: an obfuscated command, a variable or a script file can slip past a regex. It
also fails closed: a shell prompt with no readable command is never auto-approved.
"""

from __future__ import annotations

import re
from typing import Any

QUESTION_TOOL = "AskUserQuestion"
PLAN_TOOL = "ExitPlanMode"
SHELL_TOOLS = frozenset({"Bash", "PowerShell"})

# Prompts that need a person's judgement, however harmless they look.
_ALWAYS_WAIT = frozenset({QUESTION_TOOL, PLAN_TOOL})

# Words that don't bridge two commands: a flag must sit in the same simple command as its program.
_SAME_COMMAND = r"[^|;&\n]*"

_PATTERN_SOURCES = (
    # privilege escalation
    r"(?<![\w-])(sudo|su|doas|runas)(?![\w-])",
    # recursive or forced deletion
    rf"\brm\b{_SAME_COMMAND}\s(-\w*[rf]\w*|--recursive|--force)\b",
    rf"\bRemove-Item\b{_SAME_COMMAND}-(Recurse|Force)\b",
    rf"\b(del|erase|rd|rmdir)\b{_SAME_COMMAND}\s/s\b",
    # rewriting or discarding git history and work
    rf"\bgit\b{_SAME_COMMAND}\bpush\b{_SAME_COMMAND}(\s--force\S*|\s-f\b|\s\+\S)",
    rf"\bgit\b{_SAME_COMMAND}\breset\b{_SAME_COMMAND}--hard\b",
    rf"\bgit\b{_SAME_COMMAND}\bclean\b{_SAME_COMMAND}\s-\w*f",
    # running a download
    r"\b(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^\n]*\|\s*(sudo\s+)?(sh|bash|zsh|pwsh|powershell|iex|Invoke-Expression)\b",
    r"\b(iex|Invoke-Expression)\b[^\n]*\b(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod|DownloadString)\b",
    # disks
    r"\bmkfs(\.\w+)?\b",
    r"\bformat\s+[a-z]:",
    r"\bFormat-Volume\b",
    r"\bdiskpart\b",
    rf"\bdd\b{_SAME_COMMAND}\bof=",
    # permissions across a tree
    rf"\b(chmod|chown)\b{_SAME_COMMAND}\s(-\w*R|--recursive)\b",
    # taking the machine down or editing the registry
    r"\b(shutdown|reboot|poweroff)\b",
    r"\b(Restart|Stop)-Computer\b",
    r"\breg(\.exe)?\s+delete\b",
    # destructive SQL
    r"\bDROP\s+(TABLE|DATABASE)\b",
)

DANGEROUS_COMMAND_PATTERNS = tuple(re.compile(source, re.IGNORECASE) for source in _PATTERN_SOURCES)


def _command_is_safe(tool_input: dict[str, Any]) -> bool:
    """Whether a shell prompt's command is readable and matches no dangerous pattern."""
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or not command.strip():
        return False
    return not any(pattern.search(command) for pattern in DANGEROUS_COMMAND_PATTERNS)


def is_auto_approvable(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """True when auto-approve may answer this prompt `allow` without a person."""
    if tool_name in _ALWAYS_WAIT:
        return False
    if tool_name in SHELL_TOOLS:
        return _command_is_safe(tool_input)
    return True
