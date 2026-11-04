# jois-init:docs begin
"""Builds the GitHub wiki from the nested pages under `wiki/`.

Standard library only. The repo root is the parent of this script's folder (override with `--root`).

  python scripts/build_wiki.py              check the pages (flat names must be unique)
  python scripts/build_wiki.py --write-nav  regenerate `_Sidebar.md` and the page list in `Home.md`
  python scripts/build_wiki.py --out DIR    write the flat wiki pages to DIR

A page's flat name is its path under `wiki/` with the folders joined by `-` and no `.md`.
Authors write links as relative `.md` paths; `--out` rewrites them to flat names and keeps anchors.
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
MD_BEGIN = "<!-- jois-init:docs begin -->"
MD_END = "<!-- jois-init:docs end -->"
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


def page_title(wiki: Path, page: str) -> str:
    """The page's first `# ` heading, else its file name spelled out."""
    for line in (wiki / page).read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return Path(page).stem.replace("-", " ").replace("_", " ")


def nav_lines(wiki: Path, skip: tuple[str, ...]) -> list[str]:
    """The page list grouped by folder: top-level pages first, then one bold folder line per group."""
    groups: dict[str, list[str]] = {}
    for page in list_pages(wiki):
        if page not in skip:
            groups.setdefault(posixpath.dirname(page), []).append(page)
    lines: list[str] = []
    for folder in sorted(groups, key=lambda f: (f != "", f)):
        if folder:
            lines += ["", f"**{folder}**", ""]
        lines += [f"- [{page_title(wiki, p)}]({p})" for p in groups[folder]]
    return lines


def _block(lines: list[str]) -> str:
    return "\n".join([MD_BEGIN, *lines, MD_END])


def render_nav(wiki: Path) -> dict[str, str]:
    """The text `_Sidebar.md` and `Home.md` should hold, without writing anything.

    `_Sidebar.md` is generated whole. In `Home.md` only the block between the markers is
    generated; the text around it stays as it is, and a Home without the block gets one appended.
    """
    sidebar = _block([f"- [Home]({HOME})", *nav_lines(wiki, NAV_PAGES)]) + "\n"
    home_path = wiki / HOME
    home_block = _block(["## Pages", "", *nav_lines(wiki, NAV_PAGES)])
    if not home_path.is_file():
        home = f"# Home\n\n{home_block}\n"
    else:
        current = home_path.read_text(encoding="utf-8")
        begin, end = current.find(MD_BEGIN), current.find(MD_END)
        if begin != -1 and end > begin:
            home = current[:begin] + home_block + current[end + len(MD_END):]
        else:
            home = current.rstrip("\n") + "\n\n" + home_block + "\n"
    return {SIDEBAR: sidebar, HOME: home}


def write_nav(wiki: Path) -> list[str]:
    """Write the generated navigation; returns the files whose content changed."""
    changed = []
    for name, text in render_nav(wiki).items():
        path = wiki / name
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            continue
        path.write_text(text, encoding="utf-8", newline="\n")
        changed.append(name)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the GitHub wiki from wiki/.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="the repo root (default: the parent of this script's folder)")
    parser.add_argument("--out", type=Path, help="write the flat wiki pages to this folder")
    parser.add_argument("--write-nav", action="store_true",
                        help="regenerate _Sidebar.md and the page list in Home.md")
    args = parser.parse_args(argv)
    wiki = args.root.resolve() / WIKI_DIR
    if not wiki.is_dir():
        print(f"{WIKI_DIR.as_posix()}: folder not found under {args.root}")
        return 1
    try:
        check_names(list_pages(wiki))
        if args.write_nav:
            for name in write_nav(wiki):
                print(f"updated {WIKI_DIR.as_posix()}/{name}")
        if args.out:
            written = build_output(wiki, args.out)
            print(f"wrote {len(written)} page(s) to {args.out}")
    except WikiError as err:
        print(err)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
# jois-init:docs end
