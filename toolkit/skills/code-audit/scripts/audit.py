#!/usr/bin/env python3
"""Deterministic engine for /code-audit. Python 3, standard library only.

    audit.py --init   [--repo PATH] [--full]     resolve scope, snapshot the repo, create the evidence folder
    audit.py --phase 0 --evidence DIR            linters and type checkers; exit 2 on a syntax/type error
    audit.py --phase 1 --evidence DIR            gitleaks, semgrep, jscpd, trivy
    audit.py --verify --evidence DIR             compare the repo with the --init snapshot; exit 4 on any change
    audit.py --report --evidence DIR             merge all evidence into DIR/report.md and print it
    audit.py --save-agent                        SubagentStop hook: save a reviewer's JSON reply (payload on stdin)

Read-only by construction: every tool command comes from the builders below, none of which carries an
auto-fix flag (run() refuses any command that does), and tool caches are pointed at the evidence folder.
The audit covers only the repository it is launched in and writes only to <repo>/code-audit/<run>/
(self-ignored by git, excluded from scope and from the tamper check). It never touches a path outside
the working directory.

Exit codes: 0 ok, 1 usage or internal error, 2 Phase 0 gate failed, 3 nothing to audit, 4 repo changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

EXIT_OK, EXIT_ERROR, EXIT_GATE, EXIT_NOTHING, EXIT_TAMPER = 0, 1, 2, 3, 4

# Any of these in a command line means a tool could rewrite the audited code.
FIX_FLAGS = frozenset({
    "--fix", "--fix-only", "--unsafe-fixes", "--autofix", "--auto-fix", "--apply",
    "--write", "--fix-dry-run-off", "--allow-dirty", "--allow-staged", "--fix-type",
})

WORKSPACE = "code-audit"  # <repo>/code-audit/<run>/ holds all evidence, temp files and reports
DEFAULT_TIMEOUT = 300
MAX_ARG_FILES = 100  # above this, tools scan the repo root and findings are filtered to scope afterwards

PY_EXT = {".py"}
TS_EXT = {".ts", ".tsx", ".mts", ".cts"}
JS_EXT = {".js", ".jsx", ".mjs", ".cjs"}
RS_EXT = {".rs"}

INSTALL_HINTS = {
    "ruff": "pip install ruff", "mypy": "pip install mypy", "tsc": "npm install -D typescript",
    "eslint": "npm install -D eslint", "cargo": "install Rust (rustup)",
    "gitleaks": "https://github.com/gitleaks/gitleaks#installing",
    "semgrep": "pip install semgrep", "jscpd": "npm install -g jscpd",
    "trivy": "https://trivy.dev/latest/getting-started/installation/",
}


# --------------------------------------------------------------------------------------------------
# Process helpers
# --------------------------------------------------------------------------------------------------

def assert_report_only(cmd: list[str]) -> None:
    bad = [a for a in cmd if a in FIX_FLAGS or any(a.startswith(f + "=") for f in FIX_FLAGS)]
    if bad:
        raise RuntimeError(f"refusing to run a command with a fix flag {bad}: {cmd}")


def run(cmd: list[str], cwd: Path, timeout: int, extra_env: dict | None = None):
    """Run a command (argument list, never a shell string). Returns (rc, stdout, stderr)."""
    assert_report_only(cmd)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", **(extra_env or {}))
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, timeout=timeout, env=env)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def git(repo: Path, *args: str, check: bool = True) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.decode('utf-8', 'replace').strip()}")
    return p.stdout.decode("utf-8", "replace")


def find_tool(name: str, extra_dirs: list[Path] | None = None) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for d in extra_dirs or []:
        if d.is_dir():
            found = shutil.which(name, path=str(d))
            if found:
                return found
    return None


# --------------------------------------------------------------------------------------------------
# Scope
# --------------------------------------------------------------------------------------------------

def in_workspace(rel: str) -> bool:
    return rel == WORKSPACE or rel.startswith(WORKSPACE + "/")


def repo_root(path: Path) -> Path:
    return Path(git(path, "rev-parse", "--show-toplevel").strip()).resolve()


def _split_z(out: str) -> list[str]:
    return [x for x in out.split("\0") if x]


def resolve_scope(repo: Path, full: bool) -> dict:
    """Files in scope, as repo-relative posix paths. Diff mode: changed vs merge-base with main/master,
    plus uncommitted and untracked files. Falls back to full with a notice if there is no base branch."""
    notice = None
    base = None
    mode = "full" if full else "diff"
    if not full:
        for branch in ("main", "master"):
            if git(repo, "rev-parse", "--verify", "--quiet", branch, check=False).strip():
                mb = git(repo, "merge-base", branch, "HEAD", check=False).strip()
                if mb:
                    base = (branch, mb)
                    break
        if base is None:
            mode, notice = "full", "no main or master branch found; auditing the whole repository"
    if mode == "diff" and base:
        files = set(_split_z(git(repo, "diff", "--name-only", "-z", "--diff-filter=d", base[1])))
        files |= set(_split_z(git(repo, "ls-files", "-z", "--others", "--exclude-standard")))
    else:
        files = set(_split_z(git(repo, "ls-files", "-z")))
    files = {f for f in files if (repo / f).is_file() and not in_workspace(f)}
    return {
        "mode": mode, "base_branch": base[0] if base else None, "base_ref": base[1] if base else None,
        "repo": str(repo), "notice": notice, "files": sorted(files),
    }


# --------------------------------------------------------------------------------------------------
# Snapshot and tamper check
# --------------------------------------------------------------------------------------------------

def _hash_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "MISSING"


def _status_paths(out: str) -> list[str]:
    """Paths named by `git status --porcelain=v1 -z` (renames and copies carry two)."""
    parts = _split_z(out)
    paths, i = [], 0
    while i < len(parts):
        entry = parts[i]
        xy, path = entry[:2], entry[3:]
        paths.append(path)
        if "R" in xy or "C" in xy:
            i += 1
            if i < len(parts):
                paths.append(parts[i])
        i += 1
    return paths


def take_snapshot(repo: Path, scope_files: list[str]) -> dict:
    entries = [e for e in _split_z(git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all"))
               if not in_workspace(e[3:])]
    status = chr(0).join(entries)
    untracked = [u for u in _split_z(git(repo, "ls-files", "-z", "--others", "--exclude-standard"))
                 if not in_workspace(u)]
    paths = sorted(p for p in set(scope_files) | set(untracked) | set(_status_paths(status))
                   if not in_workspace(p))
    config = repo / ".git" / "config"
    return {
        "head": git(repo, "rev-parse", "HEAD", check=False).strip(),
        "status": status,
        "refs": hashlib.sha256(git(repo, "for-each-ref", "--format=%(refname) %(objectname)").encode()).hexdigest(),
        "stash": git(repo, "stash", "list", check=False),
        "git_config": _hash_file(config) if config.is_file() else "ABSENT",
        "untracked": sorted(untracked),
        "files": {p: _hash_file(repo / p) for p in paths},
    }


def diff_snapshots(before: dict, after: dict) -> list[str]:
    changes = []
    for key, label in (("head", "HEAD moved"), ("refs", "branches or tags changed"),
                       ("stash", "stash changed"), ("git_config", ".git/config changed")):
        if before[key] != after[key]:
            changes.append(label)
    for p in sorted(set(before["files"]) | set(after["files"])):
        a, b = before["files"].get(p), after["files"].get(p)
        if a == b:
            continue
        if a is None:
            # Absent from the snapshot: a new untracked file, or a tracked file that was clean and out of scope.
            changes.append(f"{'added' if p in after.get('untracked', []) else 'modified'}: {p}")
        elif b is None or b == "MISSING":
            changes.append(f"deleted: {p}")
        else:
            changes.append(f"modified: {p}")
    if before["status"] != after["status"] and not any(c.split(": ")[0] in ("added", "deleted", "modified") for c in changes):
        changes.append("git status changed (index or working tree state)")
    return changes


# --------------------------------------------------------------------------------------------------
# Command builders: the fixed table. No fix flags, caches redirected to the evidence folder.
# --------------------------------------------------------------------------------------------------

def cmd_ruff(exe: str, files: list[str]) -> list[str]:
    return [exe, "check", "--no-cache", "--output-format", "json", "--exit-zero", *files]


def cmd_mypy(exe: str, files: list[str], cache_dir: Path) -> list[str]:
    return [exe, "--cache-dir", str(cache_dir), "--no-error-summary", "--no-pretty",
            "--show-column-numbers", *files]


def cmd_tsc(exe: str, project_dir: Path) -> list[str]:
    return [exe, "--noEmit", "--incremental", "false", "--pretty", "false", "-p", str(project_dir)]


def cmd_eslint(exe: str, files: list[str]) -> list[str]:
    return [exe, "--format", "json", "--no-cache", "--no-warn-ignored", *files]


def cmd_clippy(exe: str, target_dir: Path) -> list[str]:
    return [exe, "clippy", "--message-format", "json", "--target-dir", str(target_dir)]


def cmd_gitleaks(exe: str, repo: Path, report: Path) -> list[str]:
    return [exe, "detect", "--no-git", "--source", str(repo), "--report-format", "json",
            "--report-path", str(report), "--redact", "--no-banner", "--exit-code", "0"]


def cmd_semgrep(exe: str, targets: list[str], config: str) -> list[str]:
    return [exe, "scan", "--config", config, "--json", "--metrics", "off", "--quiet",
            "--disable-version-check", "--exclude", WORKSPACE, *targets]


def cmd_jscpd(exe: str, out_dir: Path, targets: list[str]) -> list[str]:
    return [exe, "--reporters", "json", "--output", str(out_dir), "--silent", "--gitignore",
            "--ignore", f"**/{WORKSPACE}/**", *targets]


def cmd_trivy(exe: str, report: Path) -> list[str]:
    return [exe, "fs", "--format", "json", "--output", str(report), "--scanners", "vuln", "--quiet",
            "--skip-dirs", WORKSPACE, "."]


# --------------------------------------------------------------------------------------------------
# Severity mapping and normalization
# --------------------------------------------------------------------------------------------------

def map_severity(tool: str, level, rule: str | None = None) -> str:
    """Scanner level -> Critical | Medium | Low (see references/severity.md)."""
    lv = str(level).upper()
    if tool == "gitleaks":
        return "Critical"
    if tool == "semgrep":
        return {"ERROR": "Critical", "WARNING": "Medium"}.get(lv, "Low")
    if tool == "trivy":
        return {"CRITICAL": "Critical", "HIGH": "Critical", "MEDIUM": "Medium"}.get(lv, "Low")
    if tool == "jscpd":
        return "Low"
    if tool == "ruff":
        r = rule or ""
        return "Medium" if r.startswith(("F", "E9", "B", "S", "PLE")) else "Low"
    if tool == "eslint":
        return "Medium" if lv == "2" else "Low"
    if tool in ("mypy", "tsc"):
        return "Medium"
    if tool == "clippy":
        return "Medium" if lv == "ERROR" else "Low"
    return "Low"


def finding(tool, rule, severity, file, line, message) -> dict:
    return {"tool": tool, "rule": rule, "severity": severity, "file": file,
            "line": int(line) if line else 0, "message": " ".join(str(message).split())[:500]}


def to_rel(path: str, base: Path, repo: Path) -> str:
    p = Path(path)
    p = (p if p.is_absolute() else base / p)
    try:
        return p.resolve().relative_to(repo).as_posix()
    except ValueError:
        return p.as_posix()


def filter_to_scope(findings: list[dict], scope: set[str]) -> list[dict]:
    return [f for f in findings if f["file"] in scope]


def parse_ruff(out: str, base: Path, repo: Path):
    findings, gate = [], []
    for item in json.loads(out or "[]"):
        code = item.get("code")
        loc = item.get("location") or {}
        f = finding("ruff", code or "syntax-error", None, to_rel(item.get("filename", ""), base, repo),
                    loc.get("row"), item.get("message", ""))
        if code is None or str(code).startswith("E9") or code == "invalid-syntax":
            f["severity"] = "Critical"
            gate.append(f)
        else:
            f["severity"] = map_severity("ruff", None, code)
            findings.append(f)
    return findings, gate


_MYPY = re.compile(r"^(?P<file>.+?):(?P<line>\d+)(?::\d+)?: error: (?P<msg>.*?)(?:\s+\[(?P<code>[\w-]+)\])?$")


def parse_mypy(out: str, base: Path, repo: Path):
    gate = []
    for line in out.splitlines():
        m = _MYPY.match(line.strip())
        if m:
            gate.append(finding("mypy", m["code"] or "type-error", "Critical",
                                to_rel(m["file"], base, repo), m["line"], m["msg"]))
    return [], gate


_TSC = re.compile(r"^(?P<file>.+?)\((?P<line>\d+),\d+\): error (?P<code>TS\d+): (?P<msg>.*)$")


def parse_tsc(out: str, base: Path, repo: Path):
    gate = []
    for line in out.splitlines():
        m = _TSC.match(line.strip())
        if m:
            gate.append(finding("tsc", m["code"], "Critical", to_rel(m["file"], base, repo), m["line"], m["msg"]))
    return [], gate


def parse_eslint(out: str, base: Path, repo: Path):
    findings, gate = [], []
    for res in json.loads(out or "[]"):
        rel = to_rel(res.get("filePath", ""), base, repo)
        for m in res.get("messages", []):
            rule = m.get("ruleId")
            if m.get("fatal") or (rule is None and m.get("severity") == 2):
                gate.append(finding("eslint", rule or "parse-error", "Critical", rel, m.get("line"), m.get("message", "")))
            else:
                findings.append(finding("eslint", rule or "eslint", map_severity("eslint", m.get("severity")),
                                        rel, m.get("line"), m.get("message", "")))
    return findings, gate


def parse_clippy(out: str, base: Path, repo: Path):
    findings, gate = [], []
    for raw in out.splitlines():
        try:
            obj = json.loads(raw)
        except ValueError:
            continue
        if obj.get("reason") != "compiler-message":
            continue
        msg = obj.get("message", {})
        level = msg.get("level")
        if level not in ("error", "warning"):
            continue
        span = next((s for s in msg.get("spans", []) if s.get("is_primary")), None)
        if not span:
            continue
        code = (msg.get("code") or {}).get("code") or "clippy"
        f = finding("clippy", code, map_severity("clippy", level), to_rel(span["file_name"], base, repo),
                    span.get("line_start"), msg.get("message", ""))
        if level == "error":
            f["severity"] = "Critical"
            gate.append(f)
        else:
            findings.append(f)
    return findings, gate


def parse_gitleaks(report_text: str, repo: Path) -> list[dict]:
    out = []
    for item in json.loads(report_text or "[]") or []:
        out.append(finding("gitleaks", item.get("RuleID", "secret"), "Critical",
                           to_rel(item.get("File", ""), repo, repo), item.get("StartLine"),
                           item.get("Description", "possible secret")))
    return out


def parse_semgrep(out: str, repo: Path) -> list[dict]:
    res = []
    for r in json.loads(out or "{}").get("results", []):
        extra = r.get("extra", {})
        res.append(finding("semgrep", r.get("check_id", "semgrep"), map_severity("semgrep", extra.get("severity")),
                           to_rel(r.get("path", ""), repo, repo), (r.get("start") or {}).get("line"),
                           extra.get("message", "")))
    return res


def parse_jscpd(report_text: str, repo: Path, scope: set[str]) -> list[dict]:
    res = []
    for d in json.loads(report_text or "{}").get("duplicates", []):
        a, b = d.get("firstFile", {}), d.get("secondFile", {})
        fa, fb = to_rel(a.get("name", ""), repo, repo), to_rel(b.get("name", ""), repo, repo)
        first, second, line = (fa, fb, a.get("start")) if fa in scope else (fb, fa, b.get("start"))
        res.append(finding("jscpd", "duplicate-code", "Low", first, line,
                           f"{d.get('lines', '?')} duplicated lines also in {second}"))
    return res


def parse_trivy(report_text: str) -> list[dict]:
    res = []
    for r in json.loads(report_text or "{}").get("Results", []) or []:
        for v in r.get("Vulnerabilities", []) or []:
            res.append(finding("trivy", v.get("VulnerabilityID", "vuln"), map_severity("trivy", v.get("Severity")),
                               r.get("Target", ""), 0,
                               f"{v.get('PkgName', '?')} {v.get('InstalledVersion', '')}: {v.get('Title') or v.get('Description', '')}"))
    return res


# --------------------------------------------------------------------------------------------------
# Phase 0
# --------------------------------------------------------------------------------------------------

def nearest_dir(rel_file: str, markers: tuple[str, ...], repo: Path) -> Path:
    d = (repo / rel_file).parent
    while True:
        if any((d / m).exists() for m in markers):
            return d
        if d == repo or d == d.parent:
            return repo
        d = d.parent


def group_by_dir(files: list[str], markers: tuple[str, ...], repo: Path) -> dict[Path, list[str]]:
    groups: dict[Path, list[str]] = {}
    for f in files:
        groups.setdefault(nearest_dir(f, markers, repo), []).append(f)
    return groups


def _skipped(tool: str) -> dict:
    return {"status": "skipped", "reason": f"not installed ({INSTALL_HINTS.get(tool, 'install it')})"}


def run_phase0(repo: Path, evidence: Path, scope_files: list[str], timeout: int) -> dict:
    by_ext = lambda exts: [f for f in scope_files if Path(f).suffix.lower() in exts]  # noqa: E731
    py, ts, js, rs = by_ext(PY_EXT), by_ext(TS_EXT), by_ext(JS_EXT), by_ext(RS_EXT)
    tools: dict[str, dict] = {}
    findings: list[dict] = []
    gate_errors: list[dict] = []

    def attempt(cmd, cwd, parser):
        """Run one tool, parse it, never raise. A non-zero exit with no output is a crash, not a clean run."""
        t0 = time.time()
        try:
            rc, out, err = run(cmd, cwd, timeout)
            if rc != 0 and not out.strip():
                return None, {"status": "failed", "reason": f"exit {rc}: {err.strip()[-300:]}"}
            parsed = parser(out)
            return parsed, {"status": "ran", "seconds": round(time.time() - t0, 1),
                            "findings": len(parsed[0]), "gate_errors": len(parsed[1])}
        except subprocess.TimeoutExpired:
            return None, {"status": "failed", "reason": f"timed out after {timeout}s"}
        except Exception as e:  # tolerant: a broken tool must not crash the audit
            return None, {"status": "failed", "reason": f"{type(e).__name__}: {e}"}

    def merge(name, parts):
        """Combine per-project runs of one tool into one record."""
        st = [p[1] for p in parts]
        for parsed, _ in parts:
            if parsed:
                findings.extend(parsed[0])
                gate_errors.extend(parsed[1])
        bad = next((s for s in st if s["status"] == "failed"), None)
        tools[name] = bad or {"status": "ran", "findings": sum(s.get("findings", 0) for s in st),
                              "gate_errors": sum(s.get("gate_errors", 0) for s in st)}

    # Python
    if py:
        exe = find_tool("ruff", [repo / ".venv" / "Scripts", repo / ".venv" / "bin"])
        if exe:
            merge("ruff", [attempt(cmd_ruff(exe, grp), repo, lambda o: parse_ruff(o, repo, repo))
                           for grp in _chunks(py)])
        else:
            tools["ruff"] = _skipped("ruff")
        parts = []
        for d, grp in group_by_dir(py, ("mypy.ini", "pyproject.toml", "setup.cfg"), repo).items():
            mexe = find_tool("mypy", [d / ".venv" / "Scripts", d / ".venv" / "bin", repo / ".venv" / "Scripts"])
            if not mexe:
                break
            rel = [Path(os.path.relpath(repo / f, d)).as_posix() for f in grp]
            parts.append(attempt(cmd_mypy(mexe, rel, evidence / "mypy-cache"), d,
                                 lambda o, d=d: parse_mypy(o, d, repo)))
        if parts:
            merge("mypy", parts)
        else:
            tools["mypy"] = _skipped("mypy")

    # TypeScript (type check) and TypeScript/JavaScript (lint)
    if ts:
        parts = []
        for d in group_by_dir(ts, ("tsconfig.json",), repo):
            if not (d / "tsconfig.json").is_file():
                continue
            texe = find_tool("tsc", [d / "node_modules" / ".bin", repo / "node_modules" / ".bin"])
            if not texe:
                break
            parts.append(attempt(cmd_tsc(texe, d), d, lambda o, d=d: parse_tsc(o, d, repo)))
        if parts:
            merge("tsc", parts)
        else:
            tools["tsc"] = _skipped("tsc")
    if ts or js:
        parts = []
        for d, grp in group_by_dir(ts + js, ("package.json",), repo).items():
            eexe = find_tool("eslint", [d / "node_modules" / ".bin", repo / "node_modules" / ".bin"])
            if not eexe:
                break
            rel = [Path(os.path.relpath(repo / f, d)).as_posix() for f in grp]
            for chunk in _chunks(rel):
                parts.append(attempt(cmd_eslint(eexe, chunk), d, lambda o, d=d: parse_eslint(o, d, repo)))
        if parts:
            merge("eslint", parts)
        else:
            tools["eslint"] = _skipped("eslint")

    # Rust
    if rs:
        parts = []
        for d in group_by_dir(rs, ("Cargo.toml",), repo):
            cexe = find_tool("cargo")
            if not cexe:
                break
            parts.append(attempt(cmd_clippy(cexe, evidence / "cargo-target"), d,
                                 lambda o, d=d: parse_clippy(o, d, repo)))
        if parts:
            merge("clippy", parts)
        else:
            tools["clippy"] = _skipped("cargo")

    scope = set(scope_files)
    result = {
        "gate": "fail" if gate_errors else "pass",
        "gate_errors": gate_errors,
        "findings": filter_to_scope(findings, scope),
        "tools": tools,
    }
    (evidence / "phase0.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _chunks(items: list, n: int = 50):
    for i in range(0, len(items), n):
        yield items[i:i + n]


# --------------------------------------------------------------------------------------------------
# Phase 1
# --------------------------------------------------------------------------------------------------

def run_phase1(repo: Path, evidence: Path, scope_files: list[str], timeout: int, full: bool) -> dict:
    scope = set(scope_files)
    tools: dict[str, dict] = {}
    all_findings: list[dict] = []
    targets = scope_files if (not full and len(scope_files) <= MAX_ARG_FILES) else ["."]

    def execute(name, exe_name, builder, reader, extra_dirs=None):
        exe = find_tool(exe_name, extra_dirs)
        if not exe:
            tools[name] = _skipped(name)
            return
        t0 = time.time()
        try:
            cmd, report = builder(exe)
            rc, out, err = run(cmd, repo, timeout, {"SEMGREP_SEND_METRICS": "off"})
            text = report.read_text(encoding="utf-8", errors="replace") if report else out
            if rc != 0:  # every Phase 1 command is built to exit 0 even when it finds something
                raise RuntimeError(f"exit {rc}: {(err or out).strip()[-300:] or 'no output'}")
            if report is None:
                (evidence / f"{name}.raw.json").write_text(out, encoding="utf-8")
            found = filter_to_scope(reader(text), scope)
            (evidence / f"{name}.json").write_text(json.dumps(found, indent=2), encoding="utf-8")
            all_findings.extend(found)
            tools[name] = {"status": "ran", "seconds": round(time.time() - t0, 1), "findings": len(found)}
        except subprocess.TimeoutExpired:
            tools[name] = {"status": "failed", "reason": f"timed out after {timeout}s"}
        except Exception as e:
            tools[name] = {"status": "failed", "reason": f"{type(e).__name__}: {e}"}

    gl_report = evidence / "gitleaks.raw.json"
    execute("gitleaks", "gitleaks", lambda exe: (cmd_gitleaks(exe, repo, gl_report), gl_report),
            lambda text: parse_gitleaks(text, repo))

    sg_config = os.environ.get("CODE_AUDIT_SEMGREP_CONFIG", "p/default")
    execute("semgrep", "semgrep", lambda exe: (cmd_semgrep(exe, targets, sg_config), None),
            lambda text: parse_semgrep(text, repo))

    jc_dir = evidence / "jscpd-raw"
    jc_report = jc_dir / "jscpd-report.json"
    execute("jscpd", "jscpd", lambda exe: (cmd_jscpd(exe, jc_dir, targets), jc_report),
            lambda text: parse_jscpd(text, repo, scope))

    tv_report = evidence / "trivy.raw.json"
    execute("trivy", "trivy", lambda exe: (cmd_trivy(exe, tv_report), tv_report), parse_trivy)

    p0 = _load(evidence / "phase0.json") or {}
    counts = {s: sum(1 for f in all_findings + p0.get("findings", []) if f["severity"] == s)
              for s in ("Critical", "Medium", "Low")}
    summary = {"phase0_gate": p0.get("gate"), "phase0_tools": p0.get("tools", {}), "phase1_tools": tools,
               "counts": counts}
    (evidence / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


# --------------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------------

def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _cwd() -> Path:
    return Path.cwd().resolve()


def require_launch_repo(repo: Path) -> None:
    """The audit covers only the repository it was launched in. Refuse any other path."""
    if not _inside(_cwd(), repo):
        raise RuntimeError(
            f"refusing to audit {repo}: it does not contain the current working directory ({_cwd()}). "
            "The audit only covers the repository it is launched in.")


def cmd_init(args) -> int:
    repo = repo_root(Path(args.repo))
    require_launch_repo(repo)
    scope = resolve_scope(repo, args.full)
    if not scope["files"]:
        print(json.dumps({"nothing_to_audit": True, "mode": scope["mode"],
                          "message": "No changed files to audit. Re-run with --full to audit the whole repository."}))
        return EXIT_NOTHING
    workspace = repo / WORKSPACE
    workspace.mkdir(exist_ok=True)
    ignore = workspace / ".gitignore"
    if not ignore.exists():  # self-ignoring folder: git never lists anything inside it
        ignore.write_text("*" + chr(10), encoding="utf-8")
    evidence = workspace / time.strftime("%Y%m%d-%H%M%S")
    evidence.mkdir(exist_ok=False)
    (evidence / "scope.json").write_text(json.dumps(scope, indent=2), encoding="utf-8")
    (evidence / "snapshot.json").write_text(json.dumps(take_snapshot(repo, scope["files"]), indent=2), encoding="utf-8")
    print(json.dumps({"evidence": str(evidence), "mode": scope["mode"], "base": scope["base_branch"],
                      "files": len(scope["files"]), "notice": scope["notice"]}))
    return EXIT_OK


def _context(args):
    evidence = Path(args.evidence).resolve()
    scope = _load(evidence / "scope.json")
    if not scope:
        raise RuntimeError(f"{evidence} has no scope.json; run --init first")
    repo = Path(scope["repo"])
    require_launch_repo(repo)
    if not _inside(evidence, repo / WORKSPACE):
        raise RuntimeError(f"refusing {evidence}: evidence must be inside {repo / WORKSPACE}")
    return evidence, scope, repo


def cmd_phase(args) -> int:
    evidence, scope, repo = _context(args)
    if args.phase == 0:
        res = run_phase0(repo, evidence, scope["files"], args.timeout)
        print(json.dumps({"gate": res["gate"], "gate_errors": res["gate_errors"], "tools": res["tools"],
                          "findings": len(res["findings"])}, indent=2))
        return EXIT_GATE if res["gate"] == "fail" else EXIT_OK
    summary = run_phase1(repo, evidence, scope["files"], args.timeout, scope["mode"] == "full")
    print(json.dumps(summary, indent=2))
    return EXIT_OK


AGENTS = ("sec-checker", "arch-checker")
SEVERITIES = ("Critical", "Medium", "Low")
SCANNER_FILES = ("gitleaks", "semgrep", "jscpd", "trivy")
_JSON_BLOCK = re.compile(r"```json\s*(.*?)```", re.S)
_RUN_DIR = re.compile(r"code-audit[\\/](\d{8}-\d{6})")


def extract_agent_json(text: str):
    """The agent's last fenced json block, else the whole text, parsed; None if neither parses."""
    blocks = _JSON_BLOCK.findall(text or "")
    for candidate in ([blocks[-1]] if blocks else []) + [text or ""]:
        try:
            data = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(data, dict):
            return data
    return None


def cmd_save_agent(args) -> int:
    """SubagentStop hook target: save the reviewer's reply (hook payload on stdin) into its evidence folder.

    Never fails the agent: every problem is reported on stderr and the exit code is 0. A missing file
    shows up in the report as missing reviewer output.
    """
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
        name = str(payload.get("agent_type") or "").split(":")[-1]
        if name not in AGENTS:
            return EXIT_OK  # not one of ours
        text = payload.get("last_assistant_message") or ""
        data = extract_agent_json(text)
        folder = (data or {}).get("evidence")
        if not folder:
            m = _RUN_DIR.search(text)
            folder = str(_cwd() / WORKSPACE / m.group(1)) if m else None
        if not folder:
            raise RuntimeError("the reply names no evidence folder")
        evidence, _scope, _repo = _context(argparse.Namespace(evidence=folder))
        if data is None:
            (evidence / f"agent-{name}.raw.txt").write_text(text, encoding="utf-8")
            raise RuntimeError("the reply holds no parseable JSON block (raw text saved)")
        (evidence / f"agent-{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"code-audit save-agent: {e}", file=sys.stderr)
    return EXIT_OK


def _cell(value) -> str:
    return str(value if value not in (None, "") else "-").replace("|", "\\|").replace(chr(10), " ")


def _key(f: dict) -> tuple:
    return (f.get("file"), f.get("line"), f.get("source"))


def merge_findings(baseline: list[dict], agents: dict[str, dict]):
    """Apply the triage rules. Returns (findings, dismissed, adjustments, dropped)."""
    base = {}
    for f in baseline:
        source = f"{f['tool']}:{f['rule']}"
        base[(f["file"], f["line"], source)] = {
            "severity": f["severity"], "file": f["file"], "line": f["line"],
            "source": source, "message": f["message"], "fix": None, "principle": None}
    dismissed, adjustments, dropped = [], [], 0
    for name, data in agents.items():
        for d in data.get("dismissed") or []:
            if isinstance(d, dict) and d.get("reason"):
                dismissed.append({**d, "agent": name})
                base.pop(_key(d), None)
    added: dict[tuple, dict] = {}
    for name, data in agents.items():
        for f in data.get("findings") or []:
            ok = (isinstance(f, dict) and f.get("source") and f.get("file")
                  and isinstance(f.get("line"), int) and f["line"] > 0 and f.get("severity") in SEVERITIES)
            if not ok:
                dropped += 1
                continue
            row = {k: f.get(k) for k in ("severity", "file", "line", "source", "message", "fix", "principle")}
            row["agent"] = name
            prior = base.get(_key(f))
            if prior:
                if f["severity"] != prior["severity"]:
                    if f.get("reason"):
                        adjustments.append({**row, "from": prior["severity"], "reason": f["reason"]})
                    else:
                        row["severity"] = prior["severity"]  # a change needs a reason
                base[_key(f)] = {**prior, **{k: v for k, v in row.items() if v}, "severity": row["severity"]}
            else:
                added.setdefault(_key(f), row)
    return list(base.values()) + list(added.values()), dismissed, adjustments, dropped


def build_report(evidence: Path, scope: dict, repo: Path) -> tuple[str, bool]:
    """Assemble report.md from the evidence files. Returns (text, repo_unchanged)."""
    p0 = _load(evidence / "phase0.json") or {}
    summary = _load(evidence / "summary.json")
    verify = _load(evidence / "verify.json")
    gate_failed = p0.get("gate") == "fail"
    baseline = list(p0.get("findings", []))
    for tool in SCANNER_FILES:
        baseline += _load(evidence / f"{tool}.json") or []
    agents, agent_status = {}, {}
    for name in AGENTS:
        data = _load(evidence / f"agent-{name}.json")
        if gate_failed:
            agent_status[name] = "not run (Phase 0 gate failed)"
        elif isinstance(data, dict):
            agents[name] = data
            agent_status[name] = "ok"
        else:
            agent_status[name] = "output missing or unparseable"
    findings, dismissed, adjustments, dropped = merge_findings(baseline, agents)
    mode = "full" if scope["mode"] == "full" else f"diff vs {scope.get('base_branch') or 'base'}"
    changes = [] if verify is None else verify.get("changes", [])
    tampered = bool(verify) and not verify.get("ok", True)
    incomplete = [] if gate_failed else [n for n, s in agent_status.items() if s != "ok"]
    out = [f"# Code audit: {repo.name} ({mode}, {len(scope['files'])} files)", ""]
    if tampered:
        out += ["> **AUDIT INVALID: the repository changed during the audit. No result below can be trusted.**", ""]
        out += [f"- {c}" for c in changes] + [""]
    elif verify is None:
        out += ["> Tamper check was not run (`--verify`); the repository state is unconfirmed.", ""]
    if incomplete:
        out += [f"> **INCOMPLETE: reviewer output missing for {', '.join(incomplete)}.** The audit is not complete.", ""]
    if gate_failed:
        out += ["## Phase 0 gate failed", "",
                "The code has syntax or type errors. The audit stopped before Phase 1: no scanner or reviewer ran.", "",
                "| Location | Tool | Rule | Message |", "|---|---|---|---|"]
        out += [f"| {_cell(e['file'])}:{e['line']} | {_cell(e['tool'])} | {_cell(e['rule'])} | {_cell(e['message'])} |"
                for e in p0.get("gate_errors", [])]
        out += [""]
    else:
        titles = {"Critical": "Critical (blockers)", "Medium": "Medium (refactor)", "Low": "Low (tech debt)"}
        for sev in SEVERITIES:
            rows = sorted((f for f in findings if f["severity"] == sev), key=lambda f: (f["file"], f["line"]))
            out += [f"## {titles[sev]}", ""]
            if not rows:
                out += ["none", ""]
                continue
            out += ["| Location | Source | Finding | Suggested fix |", "|---|---|---|---|"]
            for f in rows:
                msg = f["message"] if not f.get("principle") else f"[{f['principle']}] {f['message']}"
                out += [f"| {_cell(f['file'])}:{f['line']} | {_cell(f['source'])} | {_cell(msg)} | {_cell(f.get('fix'))} |"]
            out += [""]
        out += ["## Dismissed as false positives", ""]
        out += [f"- {d.get('source')} {d.get('file')}:{d.get('line')}: {d['reason']} ({d['agent']})" for d in dismissed] or ["none"]
        out += ["", "## Severity adjustments", ""]
        out += [f"- {a['file']}:{a['line']} {a['source']}: {a['from']} -> {a['severity']}: {a['reason']} ({a['agent']})"
                for a in adjustments] or ["none"]
        out += [""]
        if dropped:
            out += [f"{dropped} reviewer finding(s) were dropped for lacking a source, file, positive line or valid severity.", ""]
        if not findings and not incomplete and not tampered and verify is not None:
            out += ["**Clean: no findings remain after triage.**", ""]
    out += ["## Reviewers", ""] + [f"- {n}: {s}" for n, s in agent_status.items()] + [""]
    tools = {**p0.get("tools", {}), **(summary or {}).get("phase1_tools", {})}
    notes = [f"- {t}: {v.get('status')}: {v.get('reason')}" for t, v in tools.items() if v.get("status") != "ran"]
    out += ["## Skipped or failed tools", ""] + (notes or ["none"]) + [""]
    out += ["## Scope", "", f"{mode}, base {scope.get('base_ref') or 'n/a'}, {len(scope['files'])} files; evidence at {evidence}"]
    if scope.get("notice"):
        out += ["", scope["notice"]]
    return chr(10).join(out) + chr(10), not tampered


def cmd_report(args) -> int:
    """Build <evidence>/report.md from the evidence files and print it. The only write this mode makes."""
    evidence, scope, repo = _context(args)
    text, unchanged = build_report(evidence, scope, repo)
    (evidence / "report.md").write_text(text, encoding="utf-8")
    raw = getattr(sys.stdout, "buffer", None)  # bytes keep UTF-8 intact on a Windows console
    if raw:
        raw.write(text.encode("utf-8"))
        raw.flush()
    else:
        sys.stdout.write(text)
    return EXIT_OK if unchanged else EXIT_TAMPER


def cmd_verify(args) -> int:
    evidence, scope, repo = _context(args)
    before = _load(evidence / "snapshot.json")
    if not before:
        raise RuntimeError("no snapshot.json; run --init first")
    changes = diff_snapshots(before, take_snapshot(repo, scope["files"]))
    (evidence / "verify.json").write_text(json.dumps({"ok": not changes, "changes": changes}, indent=2), encoding="utf-8")
    if changes:
        print("AUDIT INVALID: the repository changed during the audit:")
        for c in changes:
            print(f"  {c}")
        return EXIT_TAMPER
    print("OK: repository identical to the pre-audit snapshot")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init", action="store_true")
    mode.add_argument("--phase", type=int, choices=(0, 1))
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--report", action="store_true", help="build <evidence>/report.md from the evidence files")
    mode.add_argument("--save-agent", action="store_true", help="hook: save a reviewer reply from stdin")
    ap.add_argument("--repo", default=".", help="the repository to audit; must contain the current directory")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--evidence", help="evidence folder printed by --init")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="per-tool timeout in seconds")
    args = ap.parse_args(argv)
    try:
        if args.init:
            return cmd_init(args)
        if args.save_agent:
            return cmd_save_agent(args)
        if not args.evidence:
            ap.error("--evidence is required with --phase, --verify and --report")
        if args.report:
            return cmd_report(args)
        return cmd_verify(args) if args.verify else cmd_phase(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
