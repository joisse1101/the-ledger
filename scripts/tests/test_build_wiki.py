# jois-init:docs begin
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_wiki  # noqa: E402

HOME_TEXT = "# Home\n\nWelcome, written by hand.\n"


def _page(root, relative, text="# Title\n"):
    path = root / "wiki" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _tree(root):
    """A minimal wiki with a page two folders deep."""
    _page(root, "Home.md", HOME_TEXT)
    _page(root, "architecture/billing/refunds.md", "# Refunds\n\nSee [states](../orders/lifecycle.md#states).\n")
    _page(root, "architecture/orders/lifecycle.md", "# Order lifecycle\n")
    return root / "wiki"


def test_lists_pages_at_any_depth(tmp_path):
    wiki = _tree(tmp_path)
    assert build_wiki.list_pages(wiki) == [
        "Home.md",
        "architecture/billing/refunds.md",
        "architecture/orders/lifecycle.md",
    ]


def test_flat_name_joins_folders_with_hyphens():
    assert build_wiki.flat_name("architecture/billing/refunds.md") == "architecture-billing-refunds"
    assert build_wiki.flat_name("Home.md") == "Home"


def test_collision_names_both_files(tmp_path):
    wiki = _tree(tmp_path)
    _page(tmp_path, "a-b.md")
    _page(tmp_path, "a/b.md")
    with pytest.raises(build_wiki.WikiError) as err:
        build_wiki.check_names(build_wiki.list_pages(wiki))
    assert "a-b.md" in str(err.value) and "a/b.md" in str(err.value)


def test_main_fails_on_collision(tmp_path, capsys):
    _tree(tmp_path)
    _page(tmp_path, "a-b.md")
    _page(tmp_path, "a/b.md")
    assert build_wiki.main(["--root", str(tmp_path)]) == 1
    assert "a-b.md" in capsys.readouterr().out


def test_out_writes_flat_pages_for_a_nested_page(tmp_path):
    _tree(tmp_path)
    out = tmp_path / "out"
    assert build_wiki.main(["--root", str(tmp_path), "--out", str(out)]) == 0
    assert (out / "architecture-billing-refunds.md").is_file()
    assert not (out / "architecture").exists()


def test_out_rewrites_link_and_keeps_anchor(tmp_path):
    _tree(tmp_path)
    out = tmp_path / "out"
    build_wiki.main(["--root", str(tmp_path), "--out", str(out)])
    text = (out / "architecture-billing-refunds.md").read_text(encoding="utf-8")
    assert "(architecture-orders-lifecycle#states)" in text


def test_out_leaves_external_links_unknown_pages_and_code_fences(tmp_path):
    wiki = _tree(tmp_path)
    _page(tmp_path, "x.md", "[web](https://e.com/a.md) [gone](nope.md)\n```\n[c](Home.md)\n```\n")
    out = tmp_path / "out"
    build_wiki.build_output(wiki, out)
    assert (out / "x.md").read_text(encoding="utf-8") == (wiki / "x.md").read_text(encoding="utf-8")


def test_write_nav_lists_a_new_page(tmp_path):
    wiki = _tree(tmp_path)
    build_wiki.write_nav(wiki)
    _page(tmp_path, "architecture/billing/invoices.md", "# Invoices\n")
    assert "invoices.md" not in (wiki / "_Sidebar.md").read_text(encoding="utf-8")
    build_wiki.write_nav(wiki)
    assert "[Invoices](architecture/billing/invoices.md)" in (wiki / "_Sidebar.md").read_text(encoding="utf-8")
    assert "[Invoices](architecture/billing/invoices.md)" in (wiki / "Home.md").read_text(encoding="utf-8")


def test_write_nav_groups_pages_by_folder(tmp_path):
    wiki = _tree(tmp_path)
    _page(tmp_path, "Glossary.md", "# Glossary\n")
    build_wiki.write_nav(wiki)
    sidebar = (wiki / "_Sidebar.md").read_text(encoding="utf-8")
    top, billing, orders = (sidebar.index(t) for t in ("[Glossary]", "**architecture/billing**", "**architecture/orders**"))
    assert top < billing < orders
    assert sidebar.index("[Refunds]") > billing and sidebar.index("[Order lifecycle]") > orders


def test_write_nav_keeps_home_text_outside_markers(tmp_path):
    wiki = _tree(tmp_path)
    home = f"# Home\n\nIntro.\n\n{build_wiki.MD_BEGIN}\nold list\n{build_wiki.MD_END}\n\nFooter.\n"
    _page(tmp_path, "Home.md", home)
    build_wiki.write_nav(wiki)
    text = (wiki / "Home.md").read_text(encoding="utf-8")
    assert text.startswith("# Home\n\nIntro.\n\n") and text.endswith("\n\nFooter.\n")
    assert "old list" not in text and text.count(build_wiki.MD_BEGIN) == 1


def test_write_nav_appends_block_when_home_has_no_markers_and_is_idempotent(tmp_path):
    wiki = _tree(tmp_path)
    assert "Home.md" in build_wiki.write_nav(wiki)
    text = (wiki / "Home.md").read_text(encoding="utf-8")
    assert text.startswith(HOME_TEXT)
    assert build_wiki.write_nav(wiki) == []
    assert (wiki / "Home.md").read_text(encoding="utf-8") == text
# jois-init:docs end
