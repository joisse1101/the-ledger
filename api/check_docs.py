"""Checks that the project's documentation still matches the repository.

Runs over the whole repo (paths are relative to the repo root, one level above this file) but is
kept in api/ with the rest of the Python. Plain standard library; run `python check_docs.py` locally
or from CI. Exits 1 and prints one `file:line: message` per problem, else prints a one-line pass.

Checks:
  1. every relative link in a wiki page or CLAUDE.md points at a file that exists
  2. every wiki page is linked from _Sidebar.md, and from Home.md
  3. every repo path written in inline code in a wiki page or CLAUDE.md exists
  4. size budgets for the root and nested CLAUDE.md files

Paths ignored by git (.venv, dist, .ledger...) are exempt from the inline-code check. A line
containing IGNORE_MARKER is skipped by it too, for any other path deliberately absent from a checkout.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT_BUDGET_BYTES = 8 * 1024
NESTED_BUDGET_BYTES = 4 * 1024
IGNORE_MARKER = "<!-- docs-check: ignore -->"

# A token with a "/" is only treated as a repo path when its first segment is a top-level entry of
# the repo or its last segment has one of these extensions; this keeps "and/or" and the like out.
PATH_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".css", ".html", ".md", ".json", ".toml", ".txt",
    ".yml", ".yaml", ".ps1", ".sh", ".template", ".example",
}
NOT_A_PATH_CHARS = set(" \t*?{}<>$()[]=|:@%~\\,;\"'")

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CODE_RE = re.compile(r"`([^`\n]+)`")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def _prose_lines(path: Path):
    """Yield (line number, text) for every line outside fenced code blocks."""
    in_fence = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


def _wiki_pages(root: Path) -> list[Path]:
    wiki = root / "wiki"
    return sorted(wiki.glob("*.md")) if wiki.is_dir() else []


def _claude_files(root: Path) -> tuple[list[Path], list[Path]]:
    """Return (root CLAUDE.md files, nested CLAUDE.md files) — nested = one level down."""
    top = [p for p in [root / "CLAUDE.md"] if p.is_file()]
    nested = sorted(
        p
        for p in root.glob("*/CLAUDE.md")
        if p.is_file() and not p.parent.name.startswith(".")
    )
    return top, nested


def _link_target(raw: str) -> str | None:
    """The file part of a relative link, or None for URLs and in-page anchors."""
    if SCHEME_RE.match(raw) or raw.startswith(("#", "/")):
        return None
    target = raw.split("#", 1)[0].split("?", 1)[0]
    return target or None


def _links(path: Path) -> list[tuple[int, str]]:
    found = []
    for number, line in _prose_lines(path):
        for match in LINK_RE.finditer(CODE_RE.sub("", line)):
            target = _link_target(match.group(1))
            if target:
                found.append((number, target))
    return found


def check_links(root: Path, files: list[Path]) -> list[str]:
    problems = []
    for path in files:
        for number, target in _links(path):
            if not (path.parent / target).resolve().exists():
                hint = ""
                if path.parent.name == "wiki" and not target.endswith(".md"):
                    hint = " (wiki links must end in .md; the publish step strips it)"
                problems.append(
                    f"{_rel(root, path)}:{number}: link target '{target}' does not exist{hint}"
                )
    return problems


def check_orphans(root: Path) -> list[str]:
    pages = _wiki_pages(root)
    problems = []
    for required in ("Home.md", "_Sidebar.md"):
        if not (root / "wiki" / required).is_file():
            problems.append(f"wiki/{required}: required page is missing")
    if problems:
        return problems

    def linked_from(index: str) -> set[Path]:
        index_path = root / "wiki" / index
        return {(index_path.parent / t).resolve() for _, t in _links(index_path)}

    sidebar, home = linked_from("_Sidebar.md"), linked_from("Home.md")
    for page in pages:
        if page.name == "_Sidebar.md":
            continue
        resolved = page.resolve()
        if resolved not in sidebar:
            problems.append(f"{_rel(root, page)}: orphan page, not linked from wiki/_Sidebar.md")
        if page.name != "Home.md" and resolved not in home:
            problems.append(f"{_rel(root, page)}: orphan page, not linked from wiki/Home.md")
    return problems


def _repo_path_candidate(root: Path, token: str) -> str | None:
    """The repo-relative path a code span names, or None if it isn't one."""
    if "/" not in token or any(c in NOT_A_PATH_CHARS for c in token) or SCHEME_RE.match(token):
        return None
    token = token.removeprefix("./")
    if token.startswith("/"):  # an API route like /api/live, not a file
        return None
    trimmed = token.rstrip("/")
    first = trimmed.split("/", 1)[0]
    suffix = Path(trimmed).suffix
    if (root / first).exists() or suffix in PATH_EXTENSIONS:
        return trimmed
    return None


def _is_gitignored(root: Path, candidate: str) -> bool:
    """Gitignored paths (.venv, dist, .ledger...) are legitimately absent from a fresh checkout."""
    # A `dir/` pattern only matches when git is told the path is a directory, and a missing
    # path can't say, so ask about both spellings.
    for spelling in (candidate, candidate + "/"):
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "check-ignore", "-q", "--", spelling],
                capture_output=True,
                check=False,
            )
        except OSError:  # git not installed
            return False
        if result.returncode == 0:
            return True
    return False


def check_code_paths(root: Path, files: list[Path]) -> list[str]:
    problems = []
    for path in files:
        for number, line in _prose_lines(path):
            if IGNORE_MARKER in line:
                continue
            for match in CODE_RE.finditer(line):
                candidate = _repo_path_candidate(root, match.group(1))
                if (
                    candidate
                    and not (root / candidate).exists()
                    and not _is_gitignored(root, candidate)
                ):
                    problems.append(
                        f"{_rel(root, path)}:{number}: path '{candidate}' does not exist"
                    )
    return problems


def check_sizes(root: Path) -> list[str]:
    top, nested = _claude_files(root)
    problems = []
    for files, budget in ((top, ROOT_BUDGET_BYTES), (nested, NESTED_BUDGET_BYTES)):
        for path in files:
            size = path.stat().st_size
            if size > budget:
                problems.append(
                    f"{_rel(root, path)}: {size} bytes exceeds the {budget}-byte budget; "
                    "move explanation into a wiki page"
                )
    return problems


def _rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def run_checks(root: Path) -> list[str]:
    top, nested = _claude_files(root)
    docs = _wiki_pages(root) + top + nested
    return (
        check_links(root, docs)
        + check_orphans(root)
        + check_code_paths(root, docs)
        + check_sizes(root)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check docs against the repository.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root (default: the parent of this script's folder)",
    )
    root = parser.parse_args(argv).root.resolve()
    problems = run_checks(root)
    if problems:
        print("\n".join(problems))
        print(f"\ndocs check failed: {len(problems)} problem(s)")
        return 1
    print("docs check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
