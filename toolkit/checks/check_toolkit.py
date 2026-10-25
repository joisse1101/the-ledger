"""Checks that the toolkit's rules, skills and commands still follow its own standards.

Self-contained: the root is the toolkit folder (the parent of this script's folder), so the folder can
live in any repository. Plain standard library; run `python check_toolkit.py` locally or from CI.
Exits 1 and prints one `path: message` per problem (paths relative to the toolkit), else a one-line pass.

Checks:
  1. always-on rules and budgets, unscoped rules, and path-scoped technology rules
  2. the review skill: size, and that every reference it makes is in the toolkit
  3. `metadata.version` and `metadata.last_updated` on every skill, rule, agent and jois command
  4. every slash command is hidden from the session listing (`disable-model-invocation: true`)
  5. the PR body template and Author Verification sections of the write-pr and update-pr commands match
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

CORE_RULE_BUDGET_BYTES = 2 * 1024
ALWAYS_ON_BUDGET_BYTES = 4 * 1024
SCOPED_RULE_BUDGET_BYTES = 3 * 1024
SKILL_BUDGET_BYTES = 6 * 1024
ALWAYS_ON_RULES = ("core-principles.md", "architecture-boundaries.md")
SHARED_PR_SECTIONS = ("PR body template", "Author Verification")
# Loads in every session on purpose: a commit can contain no code (images, deletions, docs).
UNSCOPED_RULES = ("commit-hygiene.md",)
UNSCOPED_RULE_BUDGET_BYTES = 2 * 1024
# The core rules load only when source code is touched, so config and markup extensions are out.
CODE_EXTENSIONS = {"py", "java", "ts", "tsx", "js", "jsx", "ps1", "sh", "bat"}

# `metadata.version` in toolkit frontmatter: a semantic version, bumped by hand with `last_updated`.
SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")

CODE_RE = re.compile(r"`([^`\n]+)`")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def _rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _prose_lines(path: Path):
    """Yield (line number, text) for every line outside fenced code blocks."""
    in_fence = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


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
            problems.append(f"rules/{name}: required always-on rule is missing")
            continue
        total += path.stat().st_size
        globs = _rule_paths(path.read_text(encoding="utf-8"))
        if not globs:
            problems.append(f"rules/{name}: core rule needs `paths:` frontmatter")
        for glob in globs or []:
            if glob.rsplit(".", 1)[-1] not in CODE_EXTENSIONS:
                problems.append(f"rules/{name}: glob '{glob}' is not a source-code file type")
    core = rules / ALWAYS_ON_RULES[0]
    if core.is_file() and core.stat().st_size > CORE_RULE_BUDGET_BYTES:
        problems.append(
            f"rules/{core.name}: {core.stat().st_size} bytes exceeds the "
            f"{CORE_RULE_BUDGET_BYTES}-byte budget"
        )
    if total > ALWAYS_ON_BUDGET_BYTES:
        problems.append(
            f"rules: always-on rules total {total} bytes, over the "
            f"{ALWAYS_ON_BUDGET_BYTES}-byte budget"
        )
    return problems


def _check_unscoped_rules(rules: Path) -> list[str]:
    problems = []
    for name in UNSCOPED_RULES:
        path = rules / name
        if not path.is_file():
            continue
        rel = f"rules/{name}"
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
        rel = f"rules/{path.name}"
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


def _check_review_skill(toolkit: Path) -> list[str]:
    skill = toolkit / "skills" / "coding-standards" / "SKILL.md"
    if not skill.is_file():
        return []
    rel = "skills/coding-standards/SKILL.md"
    problems = []
    if skill.stat().st_size > SKILL_BUDGET_BYTES:
        problems.append(
            f"{rel}: {skill.stat().st_size} bytes exceeds the {SKILL_BUDGET_BYTES}-byte budget"
        )
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
            *toolkit.glob("commands/jois/*.md"),
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


def _check_commands_hidden(toolkit: Path) -> list[str]:
    """Every slash command must stay out of the session listing (user-only invocation)."""
    problems = []
    for path in sorted((toolkit / "commands").glob("**/*.md")):
        frontmatter = _frontmatter(path.read_text(encoding="utf-8")) or ""
        if not re.search(r"^disable-model-invocation:[ \t]*true[ \t]*$", frontmatter, re.MULTILINE):
            problems.append(f"{_rel(toolkit, path)}: missing `disable-model-invocation: true` in the frontmatter")
    return problems


def _check_versions(toolkit: Path) -> list[str]:
    problems = []
    for path in _versioned_items(toolkit):
        problems += _version_problems(_rel(toolkit, path), path.read_text(encoding="utf-8"))
    return problems


def _h2_section(text: str, title: str) -> str | None:
    """The text under `## title` up to the next `## ` heading outside a code fence, or None."""
    body: list[str] = []
    found = in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        elif line.startswith("## ") and not in_fence:
            if found:
                break
            found = line[3:].strip() == title
            continue
        if found:
            body.append(line)
    return "\n".join(body).strip() if found else None


def _check_shared_pr_sections(toolkit: Path) -> list[str]:
    """write-pr and update-pr each carry the PR body rules; they must not drift apart."""
    commands = toolkit / "commands" / "jois"
    write, update = commands / "write-pr.md", commands / "update-pr.md"
    if not (write.is_file() and update.is_file()):
        return []
    write_text, update_text = write.read_text(encoding="utf-8"), update.read_text(encoding="utf-8")
    return [
        f"{_rel(toolkit, write)} and {_rel(toolkit, update)}: section '{title}' differs; keep it identical in both"
        for title in SHARED_PR_SECTIONS
        if _h2_section(write_text, title) != _h2_section(update_text, title)
    ]


def run_checks(toolkit: Path) -> list[str]:
    rules = toolkit / "rules"
    if not rules.is_dir():
        return []
    return (
        _check_always_on_rules(rules)
        + _check_unscoped_rules(rules)
        + _check_scoped_rules(rules)
        + _check_review_skill(toolkit)
        + _check_versions(toolkit)
        + _check_commands_hidden(toolkit)
        + _check_shared_pr_sections(toolkit)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the toolkit against its own standards.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="toolkit folder (default: the parent of this script's folder)",
    )
    root = parser.parse_args(argv).root.resolve()
    problems = run_checks(root)
    if problems:
        print("\n".join(problems))
        return 1
    print("toolkit checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
