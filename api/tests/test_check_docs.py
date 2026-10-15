import check_docs

HIDDEN = "disable-model-invocation: true"
VERSION = 'metadata:\n  version: "1.0.0"\n  last_updated: "2026-10-14"'


def _write(root, relative, text=""):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _passing_tree(root):
    """A minimal tree on which every check passes."""
    _write(root, "api/security.py", "")
    _write(root, "wiki/Home.md", "# Home\n\n- [Security](Backend-Security.md)\n- [Home](Home.md)\n")
    _write(root, "wiki/_Sidebar.md", "[Home](Home.md)\n[Security](Backend-Security.md)\n")
    _write(root, "wiki/Backend-Security.md", "Auth lives in `api/security.py`.\n")
    _write(root, "CLAUDE.md", "| backend | [security](wiki/Backend-Security.md) |\n")
    _write(root, "api/CLAUDE.md", "| auth | [security](../wiki/Backend-Security.md) |\n")


def _problems(root):
    return check_docs.run_checks(root)


def test_all_pass(tmp_path, capsys):
    _passing_tree(tmp_path)
    assert _problems(tmp_path) == []
    assert check_docs.main(["--root", str(tmp_path)]) == 0
    assert "passed" in capsys.readouterr().out


def test_renamed_path_names_page_and_path(tmp_path, capsys):
    _passing_tree(tmp_path)
    (tmp_path / "api/security.py").rename(tmp_path / "api/auth.py")
    problems = _problems(tmp_path)
    assert problems == ["wiki/Backend-Security.md:1: path 'api/security.py' does not exist"]
    assert check_docs.main(["--root", str(tmp_path)]) == 1
    assert "api/security.py" in capsys.readouterr().out


def test_missing_route_target_names_file_and_row(tmp_path):
    _passing_tree(tmp_path)
    _write(
        tmp_path,
        "CLAUDE.md",
        "| area | page |\n|---|---|\n| web | [web](wiki/Frontend.md) |\n",
    )
    assert _problems(tmp_path) == [
        "CLAUDE.md:3: link target 'wiki/Frontend.md' does not exist"
    ]


def test_nested_claude_route_target_is_checked(tmp_path):
    _passing_tree(tmp_path)
    _write(tmp_path, "api/CLAUDE.md", "[gone](../wiki/Gone.md)\n")
    assert _problems(tmp_path) == [
        "api/CLAUDE.md:1: link target '../wiki/Gone.md' does not exist"
    ]


def test_wiki_link_without_md_suffix_is_flagged(tmp_path):
    _passing_tree(tmp_path)
    _write(tmp_path, "wiki/Backend-Security.md", "See [home](Home).\n")
    [problem] = _problems(tmp_path)
    assert "wiki/Backend-Security.md:1" in problem and "must end in .md" in problem


def test_orphan_page_is_named(tmp_path):
    _passing_tree(tmp_path)
    _write(tmp_path, "wiki/Frontend-Sessions.md", "# Sessions\n")
    problems = _problems(tmp_path)
    assert "wiki/Frontend-Sessions.md: orphan page, not linked from wiki/_Sidebar.md" in problems
    assert "wiki/Frontend-Sessions.md: orphan page, not linked from wiki/Home.md" in problems


def test_missing_home_and_sidebar(tmp_path):
    _write(tmp_path, "wiki/Other.md", "x\n")
    assert _problems(tmp_path) == [
        "wiki/Home.md: required page is missing",
        "wiki/_Sidebar.md: required page is missing",
    ]


def test_over_budget_files(tmp_path):
    _passing_tree(tmp_path)
    _write(tmp_path, "CLAUDE.md", "x" * (check_docs.ROOT_BUDGET_BYTES + 1))
    _write(tmp_path, "api/CLAUDE.md", "x" * (check_docs.NESTED_BUDGET_BYTES + 1))
    problems = _problems(tmp_path)
    assert any(p.startswith("CLAUDE.md:") and "budget" in p for p in problems)
    assert any(p.startswith("api/CLAUDE.md:") and "budget" in p for p in problems)


def test_nested_file_uses_the_smaller_budget(tmp_path):
    _passing_tree(tmp_path)
    size = check_docs.NESTED_BUDGET_BYTES + 1
    _write(tmp_path, "CLAUDE.md", "x" * size)
    assert _problems(tmp_path) == []


def test_non_paths_urls_routes_and_fences_are_skipped(tmp_path):
    _passing_tree(tmp_path)
    _write(
        tmp_path,
        "wiki/Backend-Security.md",
        "Open `https://example.com/a.py`, `GET /api/meta`, `/api/live`, `and/or`,\n"
        "`api/*.py`, `~/.claude/projects/x.jsonl` and [site](https://example.com/x).\n"
        "```\nsee `api/missing.py`\n```\n",
    )
    assert _problems(tmp_path) == []


def test_ignore_marker_skips_a_line(tmp_path):
    _passing_tree(tmp_path)
    _write(
        tmp_path,
        "wiki/Backend-Security.md",
        f"Token in `api/.ledger/token`. {check_docs.IGNORE_MARKER}\n",
    )
    assert _problems(tmp_path) == []


def test_directory_paths_and_unknown_extension_paths(tmp_path):
    _passing_tree(tmp_path)
    (tmp_path / "web/src").mkdir(parents=True)
    _write(
        tmp_path,
        "wiki/Backend-Security.md",
        "`web/src/` exists; `web/src/gone.tsx` and `api/nope/` do not.\n",
    )
    assert _problems(tmp_path) == [
        "wiki/Backend-Security.md:1: path 'web/src/gone.tsx' does not exist",
        "wiki/Backend-Security.md:1: path 'api/nope' does not exist",
    ]


def test_link_syntax_inside_code_is_not_a_link(tmp_path):
    _passing_tree(tmp_path)
    _write(tmp_path, "wiki/Backend-Security.md", "Write links as `[text](Page-Name.md)`.\n")
    assert _problems(tmp_path) == []


def test_gitignored_paths_are_exempt(tmp_path):
    import shutil
    import subprocess

    if shutil.which("git") is None:
        import pytest

        pytest.skip("git not installed")
    _passing_tree(tmp_path)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    _write(tmp_path, ".gitignore", "api/.ledger/\n")
    _write(tmp_path, "wiki/Backend-Security.md", "Token in `api/.ledger/token`, not `api/gone.py`.\n")
    assert _problems(tmp_path) == [
        "wiki/Backend-Security.md:1: path 'api/gone.py' does not exist"
    ]


def _toolkit_tree(root):
    _passing_tree(root)
    _write(root, "toolkit/rules/core-principles.md", _scoped("py"))
    _write(root, "toolkit/rules/architecture-boundaries.md", _scoped("py"))
    _write(root, "toolkit/rules/java.md", f'---\n{VERSION}\npaths:\n  - "**/*.java"\n---\nJava\n')
    _write(
        root,
        "toolkit/skills/coding-standards/SKILL.md",
        f"---\n{VERSION}\n---\nCheck against `core-principles` and `java`.\n",
    )


def _scoped(extension, padding=0):
    return f'---\n{VERSION}\npaths:\n  - "**/*.{extension}"\n---\n' + "x" * padding


def test_toolkit_tree_passes(tmp_path):
    _toolkit_tree(tmp_path)
    assert _problems(tmp_path) == []


def test_always_on_rule_budgets_and_paths(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "toolkit/rules/core-principles.md", _scoped("py", 2100))
    _write(tmp_path, "toolkit/rules/architecture-boundaries.md", "x" * 2100)
    problems = _problems(tmp_path)
    assert any("core-principles.md" in p and "2048-byte" in p for p in problems)
    assert any("architecture-boundaries.md" in p and "needs `paths:`" in p for p in problems)
    assert any("always-on rules total" in p for p in problems)


def test_core_rule_paths_must_be_source_code(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "toolkit/rules/core-principles.md", _scoped("json"))
    assert "toolkit/rules/core-principles.md: glob '**/*.json' is not a source-code file type" in _problems(
        tmp_path
    )


def test_missing_always_on_rule(tmp_path):
    _toolkit_tree(tmp_path)
    (tmp_path / "toolkit/rules/core-principles.md").unlink()
    assert "toolkit/rules/core-principles.md: required always-on rule is missing" in _problems(
        tmp_path
    )


def test_scoped_rule_needs_paths_budget_and_unique_extensions(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "toolkit/rules/noscope.md", f"---\n{VERSION}\n---\nno paths\n")
    _write(tmp_path, "toolkit/rules/big.md", _scoped("py", 3100))
    _write(tmp_path, "toolkit/rules/other.md", _scoped("java"))
    problems = _problems(tmp_path)
    assert "toolkit/rules/noscope.md: technology rule needs `paths:` frontmatter" in problems
    assert any("big.md" in p and "3072-byte" in p for p in problems)
    assert "toolkit/rules/other.md: extension 'java' is also scoped by java.md" in problems


def test_unscoped_commit_rule_is_accepted_without_paths(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "toolkit/rules/commit-hygiene.md", f"---\n{VERSION}\n---\n# Commit hygiene\n")
    assert _problems(tmp_path) == []


def test_unscoped_commit_rule_budget_and_paths(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "toolkit/rules/commit-hygiene.md", _scoped("py", 2100))
    problems = _problems(tmp_path)
    assert "toolkit/rules/commit-hygiene.md: unscoped rule must not have `paths:` frontmatter" in problems
    assert any("commit-hygiene.md" in p and "2048-byte" in p for p in problems)


def test_skill_size_and_references(tmp_path):
    _toolkit_tree(tmp_path)
    _write(
        tmp_path,
        "toolkit/skills/coding-standards/SKILL.md",
        f"---\n{VERSION}\n---\nUse `frontend-patterns` and `rules/common/coding-style.md`.\n" + "x" * 6200,
    )
    problems = _problems(tmp_path)
    assert any("6144-byte" in p for p in problems)
    assert any("'frontend-patterns' is not in the toolkit" in p for p in problems)
    assert any("'rules/common/coding-style.md' is not in the toolkit" in p for p in problems)


def _item(version='"1.0.0"', last_updated='"2026-10-14"', extra=""):
    lines = ["---"]
    if version is not None or last_updated is not None:
        lines.append("metadata:")
        if version is not None:
            lines.append(f"  version: {version}")
        if last_updated is not None:
            lines.append(f"  last_updated: {last_updated}")
    lines += [extra, "---", "Body", ""] if extra else ["---", "Body", ""]
    return "\n".join(lines)


def test_missing_and_malformed_versions_are_named(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "toolkit/rules/a.md", _item(None, None, 'paths:\n  - "**/*.toml"'))
    _write(tmp_path, "toolkit/rules/b.md", _item('"v2"', '"2026-10-14"', 'paths:\n  - "**/*.yml"'))
    _write(tmp_path, "toolkit/rules/c.md", _item('"1.0"', '"2026-10-14"', 'paths:\n  - "**/*.md"'))
    _write(tmp_path, "toolkit/rules/d.md", _item('"1.0.0"', '"2026-13-40"', 'paths:\n  - "**/*.css"'))
    _write(tmp_path, "toolkit/rules/e.md", _item('"1.0.0"', None, 'paths:\n  - "**/*.html"'))
    problems = _problems(tmp_path)
    assert "toolkit/rules/a.md: missing `metadata.version` (semver such as \"1.0.0\")" in problems
    assert any("toolkit/rules/a.md: missing `metadata.last_updated`" in p for p in problems)
    assert any("toolkit/rules/b.md: metadata.version 'v2' is not MAJOR.MINOR.PATCH" in p for p in problems)
    assert any("toolkit/rules/c.md: metadata.version '1.0' is not MAJOR.MINOR.PATCH" in p for p in problems)
    assert any("toolkit/rules/d.md: metadata.last_updated '2026-13-40' is not a date" in p for p in problems)
    assert any("toolkit/rules/e.md: missing `metadata.last_updated`" in p for p in problems)


def test_valid_metadata_passes_with_unquoted_values(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "toolkit/rules/a.md", _item("2.10.3", "2026-10-14", 'paths:\n  - "**/*.toml"'))
    assert _problems(tmp_path) == []


def test_top_level_version_is_rejected(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "toolkit/rules/a.md", '---\nversion: 1.0.0\npaths:\n  - "**/*.toml"\n---\n')
    problems = _problems(tmp_path)
    assert any(
        p.startswith("toolkit/rules/a.md: `version:` belongs under `metadata:`") for p in problems
    )


def test_version_is_required_on_skills_agents_and_review_commands(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "toolkit/skills/other/SKILL.md", "---\nname: other\n---\n")
    _write(tmp_path, "toolkit/agents/code-reviewer.md", "---\nname: code-reviewer\n---\n")
    _write(tmp_path, "toolkit/commands/jois-review/apply.md", "no frontmatter\n")
    _write(tmp_path, "toolkit/commands/opsx/apply.md", f"---\n{HIDDEN}\n---\ngenerated, not versioned by us\n")
    problems = _problems(tmp_path)
    for rel in (
        "toolkit/skills/other/SKILL.md",
        "toolkit/agents/code-reviewer.md",
        "toolkit/commands/jois-review/apply.md",
    ):
        assert any(p.startswith(f"{rel}: missing `metadata.version`") for p in problems)
    assert not any("opsx" in p for p in problems)


def test_commands_must_be_hidden_from_the_session_listing(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "toolkit/commands/opsx/apply.md", f"---\nname: a\n{HIDDEN}\n---\nbody\n")
    _write(tmp_path, "toolkit/commands/opsx/sync.md", "---\nname: s\n---\nbody\n")
    _write(
        tmp_path,
        "toolkit/commands/jois/deep/stage.md",
        "---\nname: st\ndisable-model-invocation: false\n---\n",
    )
    problems = _problems(tmp_path)
    assert any(p.startswith("toolkit/commands/opsx/sync.md: missing `disable-model-invocation") for p in problems)
    assert any(p.startswith("toolkit/commands/jois/deep/stage.md: missing `disable-model-invocation") for p in problems)
    assert not any(p.startswith("toolkit/commands/opsx/apply.md") for p in problems)


def test_jois_commands_need_a_version_but_opsx_does_not(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "toolkit/commands/jois/apply.md", f"---\n{HIDDEN}\n---\nbody\n")
    _write(tmp_path, "toolkit/commands/jois/stage.md", f"---\n{HIDDEN}\n{VERSION}\n---\nbody\n")
    _write(tmp_path, "toolkit/commands/opsx/apply.md", f"---\n{HIDDEN}\n---\nbody\n")
    problems = _problems(tmp_path)
    assert any(p.startswith("toolkit/commands/jois/apply.md: missing `metadata.version`") for p in problems)
    assert not any("jois/stage.md" in p or "opsx" in p for p in problems)


def test_skill_may_name_the_review_output_folder(tmp_path):
    _toolkit_tree(tmp_path)
    _write(
        tmp_path,
        "toolkit/skills/coding-standards/SKILL.md",
        f"---\n{VERSION}\n---\nSave to `reviews/2026-10-14_1707.md`.\n",
    )
    assert _problems(tmp_path) == []
