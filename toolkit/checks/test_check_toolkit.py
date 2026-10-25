import check_toolkit

HIDDEN = "disable-model-invocation: true"
VERSION = 'metadata:\n  version: "1.0.0"\n  last_updated: "2026-10-14"'


def _write(root, relative, text=""):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _scoped(extension, padding=0):
    return f'---\n{VERSION}\npaths:\n  - "**/*.{extension}"\n---\n' + "x" * padding


def _toolkit_tree(root):
    """A minimal toolkit on which every check passes."""
    _write(root, "rules/core-principles.md", _scoped("py"))
    _write(root, "rules/architecture-boundaries.md", _scoped("py"))
    _write(root, "rules/java.md", f'---\n{VERSION}\npaths:\n  - "**/*.java"\n---\nJava\n')
    _write(
        root,
        "skills/coding-standards/SKILL.md",
        f"---\n{VERSION}\n---\nCheck against `core-principles` and `java`.\n",
    )


def _problems(root):
    return check_toolkit.run_checks(root)


def test_toolkit_tree_passes(tmp_path, capsys):
    _toolkit_tree(tmp_path)
    assert _problems(tmp_path) == []
    assert check_toolkit.main(["--root", str(tmp_path)]) == 0
    assert "passed" in capsys.readouterr().out


def test_failure_exits_nonzero_and_names_the_file(tmp_path, capsys):
    _toolkit_tree(tmp_path)
    (tmp_path / "rules/core-principles.md").unlink()
    assert check_toolkit.main(["--root", str(tmp_path)]) == 1
    assert "rules/core-principles.md" in capsys.readouterr().out


def test_always_on_rule_budgets_and_paths(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "rules/core-principles.md", _scoped("py", 2100))
    _write(tmp_path, "rules/architecture-boundaries.md", "x" * 2100)
    problems = _problems(tmp_path)
    assert any("core-principles.md" in p and "2048-byte" in p for p in problems)
    assert any("architecture-boundaries.md" in p and "needs `paths:`" in p for p in problems)
    assert any("always-on rules total" in p for p in problems)


def test_core_rule_paths_must_be_source_code(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "rules/core-principles.md", _scoped("json"))
    assert "rules/core-principles.md: glob '**/*.json' is not a source-code file type" in _problems(
        tmp_path
    )


def test_missing_always_on_rule(tmp_path):
    _toolkit_tree(tmp_path)
    (tmp_path / "rules/core-principles.md").unlink()
    assert "rules/core-principles.md: required always-on rule is missing" in _problems(tmp_path)


def test_scoped_rule_needs_paths_budget_and_unique_extensions(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "rules/noscope.md", f"---\n{VERSION}\n---\nno paths\n")
    _write(tmp_path, "rules/big.md", _scoped("py", 3100))
    _write(tmp_path, "rules/other.md", _scoped("java"))
    problems = _problems(tmp_path)
    assert "rules/noscope.md: technology rule needs `paths:` frontmatter" in problems
    assert any("big.md" in p and "3072-byte" in p for p in problems)
    assert "rules/other.md: extension 'java' is also scoped by java.md" in problems


def test_unscoped_commit_rule_is_accepted_without_paths(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "rules/commit-hygiene.md", f"---\n{VERSION}\n---\n# Commit hygiene\n")
    assert _problems(tmp_path) == []


def test_unscoped_commit_rule_budget_and_paths(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "rules/commit-hygiene.md", _scoped("py", 2100))
    problems = _problems(tmp_path)
    assert "rules/commit-hygiene.md: unscoped rule must not have `paths:` frontmatter" in problems
    assert any("commit-hygiene.md" in p and "2048-byte" in p for p in problems)


def test_skill_size_and_references(tmp_path):
    _toolkit_tree(tmp_path)
    _write(
        tmp_path,
        "skills/coding-standards/SKILL.md",
        f"---\n{VERSION}\n---\nUse `frontend-patterns` and `rules/common/coding-style.md`.\n" + "x" * 6200,
    )
    problems = _problems(tmp_path)
    assert any("6144-byte" in p for p in problems)
    assert any("'frontend-patterns' is not in the toolkit" in p for p in problems)
    assert any("'rules/common/coding-style.md' is not in the toolkit" in p for p in problems)


def test_skill_may_name_the_review_output_folder(tmp_path):
    _toolkit_tree(tmp_path)
    _write(
        tmp_path,
        "skills/coding-standards/SKILL.md",
        f"---\n{VERSION}\n---\nSave to `reviews/2026-10-14_1707.md`.\n",
    )
    assert _problems(tmp_path) == []


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
    _write(tmp_path, "rules/a.md", _item(None, None, 'paths:\n  - "**/*.toml"'))
    _write(tmp_path, "rules/b.md", _item('"v2"', '"2026-10-14"', 'paths:\n  - "**/*.yml"'))
    _write(tmp_path, "rules/c.md", _item('"1.0"', '"2026-10-14"', 'paths:\n  - "**/*.md"'))
    _write(tmp_path, "rules/d.md", _item('"1.0.0"', '"2026-13-40"', 'paths:\n  - "**/*.css"'))
    _write(tmp_path, "rules/e.md", _item('"1.0.0"', None, 'paths:\n  - "**/*.html"'))
    problems = _problems(tmp_path)
    assert "rules/a.md: missing `metadata.version` (semver such as \"1.0.0\")" in problems
    assert any("rules/a.md: missing `metadata.last_updated`" in p for p in problems)
    assert any("rules/b.md: metadata.version 'v2' is not MAJOR.MINOR.PATCH" in p for p in problems)
    assert any("rules/c.md: metadata.version '1.0' is not MAJOR.MINOR.PATCH" in p for p in problems)
    assert any("rules/d.md: metadata.last_updated '2026-13-40' is not a date" in p for p in problems)
    assert any("rules/e.md: missing `metadata.last_updated`" in p for p in problems)


def test_valid_metadata_passes_with_unquoted_values(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "rules/a.md", _item("2.10.3", "2026-10-14", 'paths:\n  - "**/*.toml"'))
    assert _problems(tmp_path) == []


def test_top_level_version_is_rejected(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "rules/a.md", '---\nversion: 1.0.0\npaths:\n  - "**/*.toml"\n---\n')
    problems = _problems(tmp_path)
    assert any(p.startswith("rules/a.md: `version:` belongs under `metadata:`") for p in problems)


def test_version_is_required_on_skills_agents_and_review_commands(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "skills/other/SKILL.md", "---\nname: other\n---\n")
    _write(tmp_path, "agents/code-reviewer.md", "---\nname: code-reviewer\n---\n")
    _write(tmp_path, "commands/jois-review/apply.md", "no frontmatter\n")
    _write(tmp_path, "commands/opsx/apply.md", f"---\n{HIDDEN}\n---\ngenerated, not versioned by us\n")
    problems = _problems(tmp_path)
    for rel in (
        "skills/other/SKILL.md",
        "agents/code-reviewer.md",
        "commands/jois-review/apply.md",
    ):
        assert any(p.startswith(f"{rel}: missing `metadata.version`") for p in problems)
    assert not any("opsx" in p for p in problems)


def test_commands_must_be_hidden_from_the_session_listing(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "commands/opsx/apply.md", f"---\nname: a\n{HIDDEN}\n---\nbody\n")
    _write(tmp_path, "commands/opsx/sync.md", "---\nname: s\n---\nbody\n")
    _write(
        tmp_path,
        "commands/jois/deep/stage.md",
        "---\nname: st\ndisable-model-invocation: false\n---\n",
    )
    problems = _problems(tmp_path)
    assert any(p.startswith("commands/opsx/sync.md: missing `disable-model-invocation") for p in problems)
    assert any(p.startswith("commands/jois/deep/stage.md: missing `disable-model-invocation") for p in problems)
    assert not any(p.startswith("commands/opsx/apply.md") for p in problems)


def test_jois_commands_need_a_version_but_opsx_does_not(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "commands/jois/unversioned.md", f"---\n{HIDDEN}\n---\nbody\n")
    _write(tmp_path, "commands/jois/stage.md", f"---\n{HIDDEN}\n{VERSION}\n---\nbody\n")
    _write(tmp_path, "commands/opsx/apply.md", f"---\n{HIDDEN}\n---\nbody\n")
    problems = _problems(tmp_path)
    assert any(p.startswith("commands/jois/unversioned.md: missing `metadata.version`") for p in problems)
    assert not any("jois/stage.md" in p or "opsx" in p for p in problems)


def _pr_command(body):
    return (
        f"---\n{HIDDEN}\n{VERSION}\n---\n# Steps\nown steps\n\n"
        f"## PR body template\n{body}\n\n## Author Verification\nrules\n"
    )


def test_shared_pr_sections_must_match_between_write_and_update_pr(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "commands/jois/write-pr.md", _pr_command("same"))
    _write(tmp_path, "commands/jois/update-pr.md", _pr_command("changed"))
    problems = _problems(tmp_path)
    assert any(
        "PR body template" in p and "write-pr.md" in p and "update-pr.md" in p for p in problems
    )
    assert not any("Author Verification" in p for p in problems)


def test_identical_shared_pr_sections_pass(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "commands/jois/write-pr.md", _pr_command("same").replace("own steps", "a"))
    _write(tmp_path, "commands/jois/update-pr.md", _pr_command("same").replace("own steps", "b"))
    assert _problems(tmp_path) == []


def test_shared_pr_check_is_skipped_when_a_command_is_absent(tmp_path):
    _toolkit_tree(tmp_path)
    _write(tmp_path, "commands/jois/write-pr.md", _pr_command("same"))
    assert _problems(tmp_path) == []
