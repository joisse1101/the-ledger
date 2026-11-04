# jois-init:docs begin
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_wiki  # noqa: E402
import check_docs  # noqa: E402

DEEP = "wiki/architecture/billing/refunds.md"


def _file(root, relative, text="# Title\n"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _tree(root):
    """A minimal passing repo: a page two folders deep, its code file, navigation written."""
    _file(root, "wiki/Home.md", "# Home\n\nWelcome.\n")
    _file(root, DEEP, "# Refunds\n\nSee [states](../orders/lifecycle.md#states).\nCode: `src/billing/refund.py`.\n")
    _file(root, "wiki/architecture/orders/lifecycle.md", "# Order lifecycle\n")
    _file(root, "src/billing/refund.py", "")
    _file(root, "CLAUDE.md", "# Project\n")
    build_wiki.write_nav(root / "wiki")
    return root


def _problems(root):
    return check_docs.check_docs(root)


def test_minimal_tree_passes(tmp_path, capsys):
    _tree(tmp_path)
    assert _problems(tmp_path) == []
    assert check_docs.main(["--root", str(tmp_path)]) == 0
    assert "docs check passed" in capsys.readouterr().out


def test_broken_link_two_folders_deep_names_page_line_and_link(tmp_path, capsys):
    _tree(tmp_path)
    _file(tmp_path, DEEP, "# Refunds\n\nSee [gone](../orders/missing.md).\n")
    build_wiki.write_nav(tmp_path / "wiki")
    assert check_docs.main(["--root", str(tmp_path)]) == 1
    assert f"{DEEP}:3: broken link '../orders/missing.md'" in capsys.readouterr().out


def test_missing_code_path_in_a_nested_page(tmp_path):
    _tree(tmp_path)
    (tmp_path / "src/billing/refund.py").unlink()
    assert f"{DEEP}:4: path 'src/billing/refund.py' does not exist" in _problems(tmp_path)


def test_git_ignored_path_and_ignore_marker_are_exempt(tmp_path):
    _tree(tmp_path)
    (tmp_path / "src/billing/refund.py").unlink()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    _file(tmp_path, ".gitignore", "src/billing/\n")
    assert _problems(tmp_path) == []
    (tmp_path / ".gitignore").unlink()
    _file(tmp_path, DEEP, "# Refunds\n\nSee [s](../orders/lifecycle.md). `src/billing/refund.py` <!-- docs-check: ignore -->\n")
    build_wiki.write_nav(tmp_path / "wiki")
    assert _problems(tmp_path) == []


def test_paths_inside_code_fences_are_not_checked(tmp_path):
    _tree(tmp_path)
    _file(tmp_path, DEEP, "# Refunds\n\n```\n`src/none/there.py`\n```\n")
    assert _problems(tmp_path) == []


def test_orphan_nested_page_is_reported(tmp_path):
    _tree(tmp_path)
    _file(tmp_path, "wiki/architecture/billing/invoices.md")
    problems = _problems(tmp_path)
    assert "wiki/architecture/billing/invoices.md:1: orphan page, not linked from _Sidebar.md" in problems


def test_root_claude_md_over_budget(tmp_path):
    _tree(tmp_path)
    _file(tmp_path, "CLAUDE.md", "line\n" * (check_docs.ROOT_CLAUDE_LIMIT + 1))
    assert any(p.startswith("CLAUDE.md:") and "over the 200-line limit" in p for p in _problems(tmp_path))


def test_nested_claude_md_over_budget_and_within_budget(tmp_path):
    _tree(tmp_path)
    _file(tmp_path, "src/CLAUDE.md", "line\n" * check_docs.NESTED_CLAUDE_LIMIT)
    assert _problems(tmp_path) == []
    _file(tmp_path, "src/CLAUDE.md", "line\n" * (check_docs.NESTED_CLAUDE_LIMIT + 1))
    assert any(p.startswith("src/CLAUDE.md:") and "over the 100-line limit" in p for p in _problems(tmp_path))


def test_navigation_out_of_date_when_a_page_is_added_without_regenerating(tmp_path):
    _tree(tmp_path)
    _file(tmp_path, "wiki/architecture/billing/invoices.md")
    problems = _problems(tmp_path)
    assert any(p.startswith("wiki/_Sidebar.md:1: navigation is out of date") for p in problems)
    assert any(p.startswith("wiki/Home.md:1: navigation is out of date") for p in problems)


def test_navigation_passes_after_regenerating(tmp_path):
    _tree(tmp_path)
    _file(tmp_path, "wiki/architecture/billing/invoices.md")
    build_wiki.write_nav(tmp_path / "wiki")
    assert _problems(tmp_path) == []


def test_image_file_is_not_published(tmp_path):
    _tree(tmp_path)
    (tmp_path / "wiki/architecture/billing/flow.png").write_bytes(b"\x89PNG")
    assert "wiki/architecture/billing/flow.png:1: not published, only .md files reach the wiki" in _problems(tmp_path)


def test_flat_name_collision_is_reported(tmp_path):
    _tree(tmp_path)
    _file(tmp_path, "wiki/a-b.md")
    _file(tmp_path, "wiki/a/b.md")
    problems = _problems(tmp_path)
    assert len(problems) == 1 and "a-b.md" in problems[0] and "a/b.md" in problems[0]


WORKFLOW = ".github/workflows/wiki-publish.yml"
TEMPLATE_WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "wiki-publish.yml"


def test_shipped_workflow_template_passes(tmp_path):
    _tree(tmp_path)
    _file(tmp_path, WORKFLOW, TEMPLATE_WORKFLOW.read_text(encoding="utf-8"))
    assert _problems(tmp_path) == []


def test_plain_rsync_workflow_fails_naming_the_file(tmp_path):
    _tree(tmp_path)
    _file(tmp_path, WORKFLOW, "jobs:\n  publish:\n    steps:\n      - run: rsync -a wiki/ out/\n")
    problems = _problems(tmp_path)
    assert len(problems) == 1
    assert problems[0].startswith(f"{WORKFLOW}:1:") and "unrewritten" in problems[0]


def test_builder_named_only_in_a_comment_fails(tmp_path):
    _tree(tmp_path)
    _file(tmp_path, WORKFLOW, "# run python scripts/build_wiki.py --out dir\njobs: {}\n")
    assert any(p.startswith(f"{WORKFLOW}:") for p in _problems(tmp_path))


def test_absent_workflow_passes(tmp_path):
    _tree(tmp_path)
    assert not (tmp_path / WORKFLOW).exists()
    assert _problems(tmp_path) == []


def test_missing_wiki_folder_fails(tmp_path, capsys):
    assert check_docs.main(["--root", str(tmp_path)]) == 1
    assert "folder not found" in capsys.readouterr().out
# jois-init:docs end
