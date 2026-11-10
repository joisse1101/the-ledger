"""Checks that the docs under `wiki/` still match the repo.

Standard library only. The repo root is the parent of this script's folder (override with `--root`).
Exits 1 and prints one `file:line: message` per problem, else prints a one-line pass.
This repo owns this file; `/jois-init:docs` does not manage it.

Checks:
  1. every relative `.md` link in a page resolves to a page
  2. every page is linked from `Home.md` (no orphans)
  3. every repo path in inline code exists (a git-ignored path, or a line carrying
     `docs-check: ignore`, is exempt)
  4. the root and one-level-nested `CLAUDE.md` files stay within their line limits
  5. the handwritten `_Sidebar.md` links every page except `Home.md` and itself exactly once,
     and every link in it resolves
  6. no file under `wiki/` other than markdown (it would not reach the wiki)
  7. no two pages share one flat name
  8. `.github/workflows/wiki-publish.yml`, when present, has a non-comment line that runs
     `build_wiki.py --out` (without it `.md` links reach the wiki unrewritten)
  9. every link in a `CLAUDE.md` that points under `wiki/` names an existing file
"""

from __future__ import annotations

import argparse
import posixpath
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
    """True when git reports `path` as ignored. A folder that is not a git repo ignores nothing.

    A `folder/` rule only matches a missing folder when the path ends in a slash, so a path that
    is not on disk (a build folder in a fresh checkout) is also tried with one.
    """
    for candidate in (path, path.rstrip("/") + "/"):
        try:
            done = subprocess.run(
                ["git", "-C", str(root), "check-ignore", "-q", "--", candidate],
                capture_output=True, check=False,
            )
        except OSError:
            return False
        if done.returncode == 0:
            return True
    return False


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


def _page_links(wiki: Path, nav_page: str) -> list[tuple[int, str, str]]:
    """`(line number, target page, link as written)` for each page link in `nav_page`."""
    path = wiki / nav_page
    if not path.is_file():
        return []
    links = []
    for number, line in _lines_outside_fences(path.read_text(encoding="utf-8")):
        for match in build_wiki.LINK_RE.finditer(line):
            resolved = build_wiki.resolve_link(nav_page, match.group(2))
            if resolved is not None:
                links.append((number, resolved[0], match.group(2)))
    return links


def check_orphans(wiki: Path, pages: list[str]) -> list[str]:
    """Every page must be linked from `Home.md`."""
    linked = {target for _, target, _ in _page_links(wiki, build_wiki.HOME)}
    return [
        f"{_wiki_rel(page)}:1: orphan page, not linked from {build_wiki.HOME}"
        for page in pages
        if page not in build_wiki.NAV_PAGES and page not in linked
    ]


def check_sidebar(wiki: Path, pages: list[str]) -> list[str]:
    """Every page but `Home.md` and the sidebar is linked once in `_Sidebar.md`; every link resolves."""
    problems, known, counts = [], set(pages), {}
    for number, target, link in _page_links(wiki, build_wiki.SIDEBAR):
        if target not in known:
            problems.append(f"{_wiki_rel(build_wiki.SIDEBAR)}:{number}: broken link '{link}'")
        else:
            counts[target] = counts.get(target, 0) + 1
    for page in pages:
        if page in build_wiki.NAV_PAGES:
            continue
        if counts.get(page, 0) == 0:
            problems.append(f"{_wiki_rel(page)}:1: orphan page, not linked from {build_wiki.SIDEBAR}")
        elif counts[page] > 1:
            problems.append(
                f"{_wiki_rel(page)}:1: linked {counts[page]} times in {build_wiki.SIDEBAR}, expected once"
            )
    return problems


def check_claude_wiki_links(root: Path, files: list[Path]) -> list[str]:
    """Links in `CLAUDE.md` files that point under `wiki/` must name an existing file."""
    problems = []
    for file in files:
        folder = file.parent.relative_to(root).as_posix()
        for number, line in _lines_outside_fences(file.read_text(encoding="utf-8")):
            for match in build_wiki.LINK_RE.finditer(line):
                link = match.group(2)
                if build_wiki.SCHEME_RE.match(link) or link.startswith(("#", "/")):
                    continue
                target = posixpath.normpath(posixpath.join(folder, build_wiki.split_link(link)[0]))
                if target.startswith(f"{build_wiki.WIKI_DIR.as_posix()}/") and not (root / target).is_file():
                    problems.append(f"{file.relative_to(root).as_posix()}:{number}: broken wiki link '{link}'")
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
        + check_sidebar(wiki, pages)
        + check_not_published(wiki)
        + check_publish_workflow(root)
        + check_claude_wiki_links(root, claude)
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
