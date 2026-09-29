import check_docs


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
