import pytest

from app.core.remote_url import host_label, web_url


@pytest.mark.parametrize(
    "remote",
    [
        "git@github.com:acme/app.git",
        "ssh://git@github.com/acme/app.git",
        "ssh://git@github.com:22/acme/app.git",
        "https://github.com/acme/app.git",
        "https://github.com/acme/app",
        "https://github.com/acme/app/",
        "https://user:token@github.com/acme/app.git",
        "  https://GitHub.com/acme/app.git\n",
    ],
)
def test_web_url_gives_the_repo_page_for_every_remote_form(remote):
    assert web_url(remote) == "https://github.com/acme/app"


def test_web_url_keeps_a_nested_path_on_another_host():
    assert web_url("git@gitlab.com:group/sub/app.git") == "https://gitlab.com/group/sub/app"


@pytest.mark.parametrize("remote", ["", "C:/work/app", r"C:\work\app", "/srv/git/app.git", "file:///srv/app.git", "../app"])
def test_web_url_is_none_for_a_local_path(remote):
    assert web_url(remote) is None


def test_web_url_is_none_when_the_url_has_no_repo_path():
    assert web_url("https://github.com/") is None


def test_host_label_names_github():
    assert host_label("https://github.com/acme/app") == "GitHub"


def test_host_label_is_the_hostname_for_any_other_host():
    assert host_label("https://gitlab.com/acme/app") == "gitlab.com"
