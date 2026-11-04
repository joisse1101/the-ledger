"""Builds the GitHub wiki from the nested pages under `wiki/`.

Standard library only. The repo root is the parent of this script's folder (override with `--root`).

  python scripts/build_wiki.py            check the pages (flat names must be unique)
  python scripts/build_wiki.py --out DIR  write the flat wiki pages to DIR

A page's flat name is its path under `wiki/` with the folders joined by `-` and no `.md`.
Authors write links as relative `.md` paths; `--out` rewrites them to flat names and keeps anchors.
`_Sidebar.md` and `Home.md` are written by hand; `check_docs.py` checks them.
This repo owns this file; `/jois-init:docs` does not manage it.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path

WIKI_DIR = Path("wiki")
HOME = "Home.md"
SIDEBAR = "_Sidebar.md"
NAV_PAGES = (HOME, SIDEBAR)
LINK_RE = re.compile(r"(\[[^\]]*\]\()([^)\s]+)(\))")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


class WikiError(ValueError):
    """A problem with the pages that stops the build."""


def list_pages(wiki: Path) -> list[str]:
    """Every markdown page under `wiki`, at any depth, as sorted posix paths relative to it."""
    return sorted(p.relative_to(wiki).as_posix() for p in wiki.rglob("*.md") if p.is_file())


def flat_name(page: str) -> str:
    """`architecture/orders/lifecycle.md` -> `architecture-orders-lifecycle`."""
    return page[: -len(".md")].replace("/", "-")


def check_names(pages: list[str]) -> None:
    """Refuse two pages that share one flat name, naming both files."""
    seen: dict[str, str] = {}
    for page in pages:
        name = flat_name(page)
        if name in seen:
            raise WikiError(f"name collision: {seen[name]} and {page} both flatten to '{name}'")
        seen[name] = page


def split_link(link: str) -> tuple[str, str]:
    path, hash_, anchor = link.partition("#")
    return path, hash_ + anchor


def resolve_link(page: str, link: str) -> tuple[str, str] | None:
    """The target page (relative to `wiki/`) and anchor of a relative `.md` link, else None.

    None covers links that are not pages: web and mail links, anchors on the same page, and
    non-markdown targets. A target outside `wiki/` also gives None.
    """
    if SCHEME_RE.match(link) or link.startswith(("#", "/")):
        return None
    path, anchor = split_link(link)
    if not path.endswith(".md"):
        return None
    target = posixpath.normpath(posixpath.join(posixpath.dirname(page), path))
    if target.startswith(".."):
        return None
    return target, anchor


def rewrite_links(text: str, page: str, pages: set[str]) -> str:
    """Point every link to a known page at the target's flat name, keeping its anchor.

    Links inside fenced code blocks and links to unknown pages stay as written.
    """
    lines, in_fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            line = LINK_RE.sub(lambda m: _rewrite(m, page, pages), line)
        lines.append(line)
    return "\n".join(lines)


def _rewrite(match: re.Match[str], page: str, pages: set[str]) -> str:
    resolved = resolve_link(page, match.group(2))
    if resolved is None or resolved[0] not in pages:
        return match.group(0)
    target, anchor = resolved
    return f"{match.group(1)}{flat_name(target)}{anchor}{match.group(3)}"


def build_output(wiki: Path, out: Path) -> list[str]:
    """Write the flat pages to `out`; returns the file names written."""
    pages = list_pages(wiki)
    check_names(pages)
    known = set(pages)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for page in pages:
        text = (wiki / page).read_text(encoding="utf-8")
        name = f"{flat_name(page)}.md"
        (out / name).write_text(rewrite_links(text, page, known), encoding="utf-8", newline="\n")
        written.append(name)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the GitHub wiki from wiki/.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="the repo root (default: the parent of this script's folder)")
    parser.add_argument("--out", type=Path, help="write the flat wiki pages to this folder")
    args = parser.parse_args(argv)
    wiki = args.root.resolve() / WIKI_DIR
    if not wiki.is_dir():
        print(f"{WIKI_DIR.as_posix()}: folder not found under {args.root}")
        return 1
    try:
        check_names(list_pages(wiki))
        if args.out:
            written = build_output(wiki, args.out)
            print(f"wrote {len(written)} page(s) to {args.out}")
    except WikiError as err:
        print(err)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
