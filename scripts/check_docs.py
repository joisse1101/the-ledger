# jois-init:docs begin
"""Checks that the docs under `wiki/` still match the repo.

Standard library only. The repo root is the parent of this script's folder (override with `--root`).
Exits 1 and prints one `file:line: message` per problem, else prints a one-line pass.

Checks:
  1. every relative `.md` link in a page resolves to a page
  2. every page is linked from `_Sidebar.md` and `Home.md` (no orphans)
  3. every repo path in inline code exists (a git-ignored path, or a line carrying
     `docs-check: ignore`, is exempt)
  4. the root and one-level-nested `CLAUDE.md` files stay within their line limits
  5. the generated navigation is up to date (what `build_wiki.py --write-nav` would write)
  6. no file under `wiki/` other than markdown (it would not reach the wiki)
  7. no two pages share one flat name
  8. `.github/workflows/wiki-publish.yml`, when present, has a non-comment line that runs
     `build_wiki.py --out` (without it `.md` links reach the wiki unrewritten)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_wiki  # noqa: E402

IGNORE_MARKER = "docs-check: ignore"
ROOT_CLAUDE_LIMIT = 200  # lines
NESTED_CLAUDE_LIMIT = 100  # lines
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
# Looks like a repo path: two or more segments separated by `/`, no spaces or glob/template characters.
PATH_RE = re.compile(r"^(?:\./)?[\w.@-]+(?:/[\w.@-]+)+/?$")
URL_LIKE = ("http://", "https://", "//")
WORKFLOW_FILE = ".github/workflows/wiki-publish.yml"
WORKFLOW_BUILDER_WORDS = ("build_wiki.py", "--out")


def _lines_outside_fences(text: str) -> list[tuple[int, str]]:
    """`(line number, line)` for every line that is not inside a fenced code block."""
    result, in_fence = [], False
    for number, line in enumerate(text.split("\n"), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            result.append((number, line))
    return result


def is_git_ignored(root: Path, path: str) -> bool:
    """True when git reports `path` as ignored. A folder that is not a git repo ignores nothing."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", "--", path],
            capture_output=True, check=False,
        )
    except OSError:
        return False
    return done.returncode == 0


def check_links(wiki: Path, pages: list[str]) -> list[str]:
    problems, known = [], set(pages)
    for page in pages:
        text = (wiki / page).read_text(encoding="utf-8")
        for number, line in _lines_outside_fences(text):
            for match in build_wiki.LINK_RE.finditer(line):
                resolved = build_wiki.resolve_link(page, match.group(2))
                if resolved is not None and resolved[0] not in known:
                    problems.append(f"{_wiki_rel(page)}:{number}: broken link '{match.group(2)}'")
    return problems


def _linked_pages(wiki: Path, nav_page: str) -> set[str]:
    path = wiki / nav_page
    if not path.is_file():
        return set()
    linked = set()
    for match in build_wiki.LINK_RE.finditer(path.read_text(encoding="utf-8")):
        resolved = build_wiki.resolve_link(nav_page, match.group(2))
        if resolved is not None:
            linked.add(resolved[0])
    return linked


def check_orphans(wiki: Path, pages: list[str]) -> list[str]:
    problems = []
    for nav_page in build_wiki.NAV_PAGES:
        linked = _linked_pages(wiki, nav_page)
        for page in pages:
            if page not in build_wiki.NAV_PAGES and page not in linked:
                problems.append(f"{_wiki_rel(page)}:1: orphan page, not linked from {nav_page}")
    return problems


def check_paths(root: Path, files: list[Path]) -> list[str]:
    """Inline-code repo paths that do not exist, for each markdown file in `files`."""
    problems = []
    for file in files:
        text = file.read_text(encoding="utf-8")
        for number, line in _lines_outside_fences(text):
            if IGNORE_MARKER in line:
                continue
            for span in INLINE_CODE_RE.findall(line):
                if not PATH_RE.match(span) or span.startswith(URL_LIKE):
                    continue
                target = span.removeprefix("./")
                if (root / target).exists() or is_git_ignored(root, target):
                    continue
                problems.append(f"{file.relative_to(root).as_posix()}:{number}: path '{span}' does not exist")
    return problems


def claude_files(root: Path) -> list[Path]:
    """The root `CLAUDE.md` and the ones one folder down (hidden folders are skipped)."""
    nested = [p for p in sorted(root.glob("*/CLAUDE.md")) if not p.parent.name.startswith(".")]
    return ([root / "CLAUDE.md"] if (root / "CLAUDE.md").is_file() else []) + nested


def check_claude_sizes(root: Path, files: list[Path]) -> list[str]:
    problems = []
    for file in files:
        limit = ROOT_CLAUDE_LIMIT if file.parent == root else NESTED_CLAUDE_LIMIT
        count = len(file.read_text(encoding="utf-8").splitlines())
        if count > limit:
            problems.append(f"{file.relative_to(root).as_posix()}:{limit + 1}: {count} lines, over the {limit}-line limit")
    return problems


def check_navigation(wiki: Path) -> list[str]:
    problems = []
    for name, expected in build_wiki.render_nav(wiki).items():
        path = wiki / name
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            problems.append(
                f"{_wiki_rel(name)}:1: navigation is out of date; run `python scripts/build_wiki.py --write-nav`"
            )
    return problems


def check_not_published(wiki: Path) -> list[str]:
    return [
        f"{_wiki_rel(path.relative_to(wiki).as_posix())}:1: not published, only .md files reach the wiki"
        for path in sorted(wiki.rglob("*"))
        if path.is_file() and path.suffix != ".md" and not path.name.startswith(".")
    ]


def check_publish_workflow(root: Path) -> list[str]:
    """The publish workflow must run the builder, or `.md` links reach the wiki unrewritten."""
    path = root / WORKFLOW_FILE
    if not path.is_file():
        return []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("#") and all(word in line for word in WORKFLOW_BUILDER_WORDS):
            return []
    return [
        f"{WORKFLOW_FILE}:1: no step runs `build_wiki.py --out`, so `.md` links would reach the wiki unrewritten"
    ]


def check_docs(root: Path) -> list[str]:
    wiki = root / build_wiki.WIKI_DIR
    if not wiki.is_dir():
        return [f"{build_wiki.WIKI_DIR.as_posix()}: folder not found under {root}"]
    pages = build_wiki.list_pages(wiki)
    try:
        build_wiki.check_names(pages)
    except build_wiki.WikiError as err:
        return [f"{build_wiki.WIKI_DIR.as_posix()}: {err}"]
    claude = claude_files(root)
    return (
        check_links(wiki, pages)
        + check_orphans(wiki, pages)
        + check_paths(root, [wiki / p for p in pages] + claude)
        + check_claude_sizes(root, claude)
        + check_navigation(wiki)
        + check_not_published(wiki)
        + check_publish_workflow(root)
    )


def _wiki_rel(page: str) -> str:
    return f"{build_wiki.WIKI_DIR.as_posix()}/{page}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check wiki/ against the repo.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="the repo root (default: the parent of this script's folder)")
    root = parser.parse_args(argv).root.resolve()
    problems = check_docs(root)
    if problems:
        print("\n".join(problems))
        print(f"\ndocs check failed: {len(problems)} problem(s)")
        return 1
    print("docs check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
# jois-init:docs end
