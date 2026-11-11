"""Tripwire: every process the Ledger starts must carry a no-window marker on the same call.

A text and syntax scan, not proof. It stops a contributor who adds a process start that could open a
console window, and makes them either add the marker or name the window in `ALLOWED` with a reason.

Markers per language:
- Python: `creationflags=NO_WINDOW` on `subprocess.run/Popen/call/check_call/check_output`, and on a
  call through an injected starter (a parameter defaulting to one of those, or `self.<attr>` set from it).
- PowerShell: `-NoNewWindow` on `Start-Process` (it sets `CreateNoWindow` on the child), and
  `$info.CreateNoWindow = $true` for a `ProcessStartInfo`. `-WindowStyle Hidden` is not a marker:
  Windows Terminal, as the default terminal, ignores it.
- VBScript: window style `0` as the second argument of `.Run`; `.Exec` always shows a console.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = ("hooks", "widget", "api/app")
# The root start scripts and the helper they dot-source. `scripts/*.py` is docs tooling a developer
# runs in their own terminal, so it is not a background process.
SCAN_GLOBS = ("*.ps1", "scripts/*.ps1")
SKIP_DIRS = {"node_modules", ".venv", "dist", "out", "__pycache__", "tests", ".scratch"}
SUFFIXES = {".py", ".ps1", ".vbs"}

# (repo-relative path, text that identifies the line, why a window is acceptable)
ALLOWED: list[tuple[str, str, str]] = [
    ("Start-Ledger.ps1", "$backendPid = (Start-Process powershell", "the backend log window the user asked to watch"),
    ("Start-Ledger.ps1", "$frontendProc = Start-Process powershell", "the frontend log window the user asked to watch"),
    ("widget/Start-Widget.ps1", "Start-Process -FilePath $electronExe", "the widget's own window; Electron opens no console"),
]

SUBPROCESS_STARTS = {"run", "Popen", "call", "check_call", "check_output"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    text: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.text}"


def _is_test_file(path: Path) -> bool:
    name = path.name
    return name.startswith("test_") or name.startswith("Test-") or ".test." in name


def iter_files(root: Path) -> list[Path]:
    files = [p for pattern in SCAN_GLOBS for p in root.glob(pattern) if p.is_file()]
    for top in SCAN_DIRS:
        base = root / top
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            rel_parts = path.relative_to(root).parts
            if any(part in SKIP_DIRS for part in rel_parts):
                continue
            if path.is_file() and path.suffix.lower() in SUFFIXES and not _is_test_file(path):
                files.append(path)
    return sorted(set(files))


# ---------------------------------------------------------------- Python


def _is_subprocess_start(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "subprocess"
        and node.attr in SUBPROCESS_STARTS
    )


def _injected_starters(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Parameter names that default to a subprocess start, and the `self` attributes set from them."""
    params: set[str] = set()
    attrs: set[str] = set()
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = func.args
        positional = args.posonlyargs + args.args
        pairs = list(zip(positional[len(positional) - len(args.defaults):], args.defaults))
        pairs += [(a, d) for a, d in zip(args.kwonlyargs, args.kw_defaults) if d is not None]
        local = {a.arg for a, d in pairs if _is_subprocess_start(d)}
        params |= local
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id in local:
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                        attrs.add(target.attr)
    return params, attrs


def scan_python(source: str) -> list[int]:
    tree = ast.parse(source)
    params, attrs = _injected_starters(tree)
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        starts = (
            _is_subprocess_start(func)
            or (isinstance(func, ast.Name) and func.id in params)
            or (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "self"
                and func.attr in attrs
            )
        )
        if not starts:
            continue
        guarded = any(kw.arg == "creationflags" and "NO_WINDOW" in ast.unparse(kw.value) for kw in node.keywords)
        if not guarded:
            lines.append(node.lineno)
    return lines


# ---------------------------------------------------------------- PowerShell

_START_PROCESS = re.compile(r"\bStart-Process\b", re.IGNORECASE)
_NO_NEW_WINDOW = re.compile(r"-NoNewWindow\b", re.IGNORECASE)
_START_INFO = re.compile(
    r"(?:(\$\w+)\s*=\s*)?(?:New-Object\s+(?:System\.)?Diagnostics\.ProcessStartInfo\b"
    r"|\[(?:System\.)?Diagnostics\.ProcessStartInfo\]::new\b)",
    re.IGNORECASE,
)


def _logical_lines(source: str) -> list[tuple[int, str]]:
    """(first line number, text) per statement, joining backtick continuations and dropping comments."""
    result: list[tuple[int, str]] = []
    pending: tuple[int, str] | None = None
    for number, raw in enumerate(source.splitlines(), start=1):
        line = raw.rstrip()
        if line.lstrip().startswith("#") and pending is None:
            continue
        if pending is not None:
            pending = (pending[0], pending[1] + " " + line.strip())
        else:
            pending = (number, line.strip())
        if pending[1].endswith("`"):
            pending = (pending[0], pending[1][:-1])
            continue
        result.append(pending)
        pending = None
    if pending is not None:
        result.append(pending)
    return result


def scan_powershell(source: str) -> list[int]:
    lines: list[int] = []
    for number, text in _logical_lines(source):
        if _START_PROCESS.search(text) and not _NO_NEW_WINDOW.search(text):
            lines.append(number)
        match = _START_INFO.search(text)
        if match:
            var = match.group(1)
            marker = var and re.search(
                re.escape(var) + r"\.CreateNoWindow\s*=\s*\$true\b", source, re.IGNORECASE
            )
            if not marker:
                lines.append(number)
    return lines


# ---------------------------------------------------------------- VBScript

_VBS_RUN = re.compile(r"\.Run\s*\(?\s*([^,]+?)(?:\s*,\s*([^,)]+))?(?:\s*,[^)]*)?\)?\s*$", re.IGNORECASE)
_VBS_EXEC = re.compile(r"\.Exec\b", re.IGNORECASE)


def scan_vbscript(source: str) -> list[int]:
    lines: list[int] = []
    for number, raw in enumerate(source.splitlines(), start=1):
        line = raw.strip()
        if line.startswith("'"):
            continue
        if _VBS_EXEC.search(line):
            lines.append(number)
            continue
        match = _VBS_RUN.search(line)
        if match and (match.group(2) or "").strip() != "0":
            lines.append(number)
    return lines


# ---------------------------------------------------------------- the scan

SCANNERS = {".py": scan_python, ".ps1": scan_powershell, ".vbs": scan_vbscript}


def find_unguarded_starts(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files(root):
        source = path.read_text(encoding="utf-8-sig", errors="replace")
        text_lines = source.splitlines()
        for number in SCANNERS[path.suffix.lower()](source):
            findings.append(Finding(path.relative_to(root).as_posix(), number, text_lines[number - 1].strip()))
    return findings


def _is_allowed(finding: Finding) -> bool:
    return any(finding.path == path and marker in finding.text for path, marker, _ in ALLOWED)


def test_every_process_start_opens_no_window() -> None:
    leaks = [f for f in find_unguarded_starts(ROOT) if not _is_allowed(f)]
    assert not leaks, (
        "Process starts with no no-window marker (add the marker, or add the line to ALLOWED with a "
        "reason; see hooks/CLAUDE.md):\n" + "\n".join(str(f) for f in leaks)
    )


def test_every_allow_list_entry_still_matches_a_start() -> None:
    findings = find_unguarded_starts(ROOT)
    stale = [
        (path, marker)
        for path, marker, _ in ALLOWED
        if not any(f.path == path and marker in f.text for f in findings)
    ]
    assert not stale, f"ALLOWED entries that match no process start any more: {stale}"


# ---------------------------------------------------------------- the scanner itself


@pytest.mark.parametrize(
    ("relative", "source", "line"),
    [
        ("api/app/leak.py", "import subprocess\n\nsubprocess.run(['code'])\n", 3),
        ("api/app/leak.py", "import subprocess\nsubprocess.Popen(\n    ['code'],\n    shell=True,\n)\n", 2),
        (
            "api/app/leak.py",
            "import subprocess\nclass C:\n    def __init__(self, run=subprocess.run):\n"
            "        self._run = run\n    def go(self):\n        self._run(['git'])\n",
            6,
        ),
        ("hooks/leak.ps1", "# a start\nStart-Process notepad -WindowStyle Hidden\n", 2),
        ("hooks/leak.ps1", "Start-Process powershell `\n    -ArgumentList '-NoExit'\n", 1),
        ("widget/leak.ps1", "$i = New-Object System.Diagnostics.ProcessStartInfo\n$i.FileName = 'x'\n", 1),
        ("Leak.ps1", "Start-Process cmd\n", 1),
        ("scripts/Leak.ps1", "Start-Process cmd\n", 1),
        ("hooks/leak.vbs", "Set s = CreateObject(\"WScript.Shell\")\ns.Run cmd, 1, False\n", 2),
        ("hooks/leak.vbs", "s.Run cmd\n", 1),
        ("hooks/leak.vbs", "Set e = s.Exec(cmd)\n", 1),
    ],
)
def test_scan_flags_an_unguarded_start(tmp_path: Path, relative: str, source: str, line: int) -> None:
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    assert [(f.path, f.line) for f in find_unguarded_starts(tmp_path)] == [(relative, line)]


@pytest.mark.parametrize(
    ("relative", "source"),
    [
        ("api/app/ok.py", "import subprocess\nfrom x import NO_WINDOW\nsubprocess.run(['git'], creationflags=NO_WINDOW)\n"),
        (
            "api/app/ok.py",
            "import subprocess\nclass C:\n    def __init__(self, popen=subprocess.Popen):\n"
            "        self._popen = popen\n    def go(self):\n        self._popen(\n            ['x'],\n"
            "            creationflags=NO_WINDOW,\n        )\n",
        ),
        ("api/app/ok.py", "class T:\n    def _run(self):\n        pass\n    def go(self):\n        self._run()\n"),
        ("hooks/ok.ps1", "Start-Process code -ArgumentList 'x' `\n    -NoNewWindow\n"),
        ("hooks/ok.ps1", "$i = New-Object System.Diagnostics.ProcessStartInfo\n$i.CreateNoWindow = $true\n"),
        ("hooks/ok.ps1", "# Start-Process is mentioned in a comment only\n"),
        ("hooks/ok.vbs", "objShell.Run cmd, 0, False\n' objShell.Run cmd, 1\n"),
        ("hooks/tests/Test-Leak.ps1", "Start-Process cmd\n"),
        ("api/app/test_leak.py", "import subprocess\nsubprocess.run(['x'])\n"),
        ("widget/node_modules/pkg/x.ps1", "Start-Process cmd\n"),
        ("elsewhere/leak.ps1", "Start-Process cmd\n"),
        ("scripts/check.py", "import subprocess\nsubprocess.run(['git'])\n"),
    ],
)
def test_scan_passes_a_guarded_or_out_of_scope_start(tmp_path: Path, relative: str, source: str) -> None:
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    assert find_unguarded_starts(tmp_path) == []
