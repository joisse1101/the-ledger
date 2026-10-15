"""Checks that the project's documentation still matches the repository.

Runs over the whole repo (paths are relative to the repo root, one level above this file) but is
kept in api/ with the rest of the Python. Plain standard library; run `python check_docs.py` locally
or from CI. Exits 1 and prints one `file:line: message` per problem, else prints a one-line pass.

Checks:
  1. every relative link in a wiki page or CLAUDE.md points at a file that exists
  2. every wiki page is linked from _Sidebar.md, and from Home.md
  3. every repo path written in inline code in a wiki page or CLAUDE.md exists
  4. size budgets for the root and nested CLAUDE.md files
  5. toolkit standards: always-on rules and budgets, scoped rules, review skill size and references,
     and `metadata.version` and `metadata.last_updated` on every skill, rule, agent and jois-review command

Paths ignored by git (.venv, dist, .ledger...) are exempt from the inline-code check. A line
containing IGNORE_MARKER is skipped by it too, for any other path deliberately absent from a checkout.
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT_BUDGET_BYTES = 8 * 1024
NESTED_BUDGET_BYTES = 4 * 1024
IGNORE_MARKER = "<!-- docs-check: ignore -->"
CORE_RULE_BUDGET_BYTES = 2 * 1024
ALWAYS_ON_BUDGET_BYTES = 4 * 1024
SCOPED_RULE_BUDGET_BYTES = 3 * 1024
SKILL_BUDGET_BYTES = 6 * 1024
ALWAYS_ON_RULES = ("core-principles.md", "architecture-boundaries.md")
# Loads in every session on purpose: a commit can contain no code (images, deletions, docs).
UNSCOPED_RULES = ("commit-hygiene.md",)
UNSCOPED_RULE_BUDGET_BYTES = 2 * 1024
# The core rules load only when source code is touched, so config and markup extensions are out.
CODE_EXTENSIONS = {"py", "java", "ts", "tsx", "js", "jsx", "ps1", "sh", "bat"}

# `metadata.version` in toolkit frontmatter: a semantic version, bumped by hand with `last_updated`.
SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")

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


def _rule_paths(text: str) -> list[str] | None:
    """The globs in a rule's `paths:` frontmatter, or None if it has none."""
    match = re.match(r"---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    if not match:
        return None
    block = re.search(r"^paths:[ \t]*\r?\n((?:[ \t]+-[ \t]*.+\r?\n?)+)", match.group(1) + "\n", re.MULTILINE)
    if not block:
        return None
    return [g.strip().strip("\"'") for g in re.findall(r"-[ \t]*(.+)", block.group(1))]


def _check_always_on_rules(rules: Path) -> list[str]:
    problems = []
    total = 0
    for name in ALWAYS_ON_RULES:
        path = rules / name
        if not path.is_file():
            problems.append(f"toolkit/rules/{name}: required always-on rule is missing")
            continue
        total += path.stat().st_size
        globs = _rule_paths(path.read_text(encoding="utf-8"))
        if not globs:
            problems.append(f"toolkit/rules/{name}: core rule needs `paths:` frontmatter")
        for glob in globs or []:
            if glob.rsplit(".", 1)[-1] not in CODE_EXTENSIONS:
                problems.append(f"toolkit/rules/{name}: glob '{glob}' is not a source-code file type")
    core = rules / ALWAYS_ON_RULES[0]
    if core.is_file() and core.stat().st_size > CORE_RULE_BUDGET_BYTES:
        problems.append(
            f"toolkit/rules/{core.name}: {core.stat().st_size} bytes exceeds the "
            f"{CORE_RULE_BUDGET_BYTES}-byte budget"
        )
    if total > ALWAYS_ON_BUDGET_BYTES:
        problems.append(
            f"toolkit/rules: always-on rules total {total} bytes, over the "
            f"{ALWAYS_ON_BUDGET_BYTES}-byte budget"
        )
    return problems


def _check_unscoped_rules(rules: Path) -> list[str]:
    problems = []
    for name in UNSCOPED_RULES:
        path = rules / name
        if not path.is_file():
            continue
        rel = f"toolkit/rules/{name}"
        if _rule_paths(path.read_text(encoding="utf-8")):
            problems.append(f"{rel}: unscoped rule must not have `paths:` frontmatter")
        if path.stat().st_size > UNSCOPED_RULE_BUDGET_BYTES:
            problems.append(
                f"{rel}: {path.stat().st_size} bytes exceeds the "
                f"{UNSCOPED_RULE_BUDGET_BYTES}-byte budget"
            )
    return problems


def _check_scoped_rules(rules: Path) -> list[str]:
    problems = []
    seen: dict[str, str] = {}
    for path in sorted(rules.glob("*.md")):
        if path.name in ALWAYS_ON_RULES or path.name in UNSCOPED_RULES:
            continue
        rel = f"toolkit/rules/{path.name}"
        globs = _rule_paths(path.read_text(encoding="utf-8"))
        if not globs:
            problems.append(f"{rel}: technology rule needs `paths:` frontmatter")
        if path.stat().st_size > SCOPED_RULE_BUDGET_BYTES:
            problems.append(
                f"{rel}: {path.stat().st_size} bytes exceeds the "
                f"{SCOPED_RULE_BUDGET_BYTES}-byte budget"
            )
        for glob in globs or []:
            ext = glob.rsplit(".", 1)[-1]
            if ext in seen and seen[ext] != path.name:
                problems.append(f"{rel}: extension '{ext}' is also scoped by {seen[ext]}")
            seen.setdefault(ext, path.name)
    return problems


def _check_review_skill(root: Path) -> list[str]:
    skill = root / "toolkit" / "skills" / "coding-standards" / "SKILL.md"
    if not skill.is_file():
        return []
    rel = "toolkit/skills/coding-standards/SKILL.md"
    problems = []
    if skill.stat().st_size > SKILL_BUDGET_BYTES:
        problems.append(
            f"{rel}: {skill.stat().st_size} bytes exceeds the {SKILL_BUDGET_BYTES}-byte budget"
        )
    toolkit = root / "toolkit"
    for number, line in _prose_lines(skill):
        for token in CODE_RE.findall(line):
            if re.fullmatch(r"[a-z]+(-[a-z]+)+", token):
                if not (toolkit / "rules" / f"{token}.md").is_file() and not (
                    toolkit / "skills" / token
                ).is_dir():
                    problems.append(f"{rel}:{number}: reference '{token}' is not in the toolkit")
            elif token.startswith("reviews/"):
                continue  # where a review is written in the reviewed repository, not a toolkit file
            elif "/" in token and not (toolkit / token).exists():
                problems.append(f"{rel}:{number}: path '{token}' is not in the toolkit")
    return problems


def _frontmatter(text: str) -> str | None:
    match = re.match(r"---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    return match.group(1) if match else None


def _metadata(frontmatter: str) -> dict[str, str]:
    """The string keys of a frontmatter `metadata:` map (flat, as the Agent Skills format keeps it)."""
    block = re.search(r"^metadata:[ \t]*\r?\n((?:[ \t]+\S.*\r?\n?)+)", frontmatter + "\n", re.MULTILINE)
    if not block:
        return {}
    pairs = re.findall(r"^[ \t]+([\w-]+):[ \t]*(.*?)[ \t]*$", block.group(1), re.MULTILINE)
    return {key: value.strip("\"'") for key, value in pairs}


def _is_date(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _versioned_items(toolkit: Path) -> list[Path]:
    return sorted(
        [
            *toolkit.glob("rules/*.md"),
            *toolkit.glob("skills/*/SKILL.md"),
            *toolkit.glob("agents/*.md"),
            *toolkit.glob("commands/jois-review/*.md"),
        ]
    )


def _version_problems(rel: str, text: str) -> list[str]:
    frontmatter = _frontmatter(text) or ""
    if re.search(r"^version:", frontmatter, re.MULTILINE):
        return [f"{rel}: `version:` belongs under `metadata:`, not at the top level of the frontmatter"]
    metadata = _metadata(frontmatter)
    problems = []
    version = metadata.get("version")
    if version is None:
        problems.append(f"{rel}: missing `metadata.version` (semver such as \"1.0.0\")")
    elif not SEMVER_RE.fullmatch(version):
        problems.append(f"{rel}: metadata.version '{version}' is not MAJOR.MINOR.PATCH")
    updated = metadata.get("last_updated")
    if updated is None:
        problems.append(f"{rel}: missing `metadata.last_updated` (a date such as 2026-10-14)")
    elif not _is_date(updated):
        problems.append(f"{rel}: metadata.last_updated '{updated}' is not a date like 2026-10-14")
    return problems


def _check_commands_hidden(root: Path) -> list[str]:
    """Every slash command must stay out of the session listing (user-only invocation)."""
    problems = []
    for path in sorted((root / "toolkit" / "commands").glob("**/*.md")):
        frontmatter = _frontmatter(path.read_text(encoding="utf-8")) or ""
        if not re.search(r"^disable-model-invocation:[ 	]*true[ 	]*$", frontmatter, re.MULTILINE):
            problems.append(f"{_rel(root, path)}: missing `disable-model-invocation: true` in the frontmatter")
    return problems


def _check_versions(root: Path) -> list[str]:
    problems = []
    for path in _versioned_items(root / "toolkit"):
        problems += _version_problems(_rel(root, path), path.read_text(encoding="utf-8"))
    return problems


def check_toolkit(root: Path) -> list[str]:
    rules = root / "toolkit" / "rules"
    if not rules.is_dir():
        return []
    return (
        _check_always_on_rules(rules)
        + _check_unscoped_rules(rules)
        + _check_scoped_rules(rules)
        + _check_review_skill(root)
        + _check_versions(root)
        + _check_commands_hidden(root)
    )


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
        + check_toolkit(root)
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
