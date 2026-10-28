"""RepoCli with a fake `run`: the commands it issues and how it answers each failure."""

import subprocess
from pathlib import Path

from app.infra.repo_cli import LIST_LIMIT, OpenCounts, RepoCli


class FakeRun:
    """Answers each command by its program, plus the subcommand for `gh` (e.g. "gh issue"), and records the calls."""

    def __init__(self, answers):
        self.answers = answers
        self.calls: list[tuple[list[str], dict]] = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        key = " ".join(command[:2]) if command[0] == "gh" else command[0]
        answer = self.answers[key]
        if isinstance(answer, BaseException):
            raise answer
        returncode, stdout = answer
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="not logged in")


def _cli(**answers):
    run = FakeRun({key.replace("_", " "): value for key, value in answers.items()})
    return RepoCli(run=run), run


def test_remote_url_is_the_trimmed_origin_url():
    cli, run = _cli(git=(0, "git@github.com:acme/app.git\n"))

    assert cli.remote_url("/work/app") == "git@github.com:acme/app.git"
    assert run.calls[0][0] == ["git", "-C", "/work/app", "remote", "get-url", "origin"]


def test_remote_url_is_none_when_there_is_no_origin():
    cli, _ = _cli(git=(2, ""))

    assert cli.remote_url("/work/app") is None


def test_remote_url_is_none_when_git_is_missing():
    cli, _ = _cli(git=FileNotFoundError("git"))

    assert cli.remote_url("/work/app") is None


def test_open_counts_count_the_listed_issues_and_pull_requests():
    cli, run = _cli(gh_issue=(0, '[{"number": 1}, {"number": 4}, {"number": 9}]'), gh_pr=(0, '[{"number": 7}]'))

    assert cli.open_counts("/work/app") == OpenCounts(issues=3, prs=1)
    command, kwargs = run.calls[0]
    assert command == ["gh", "issue", "list", "--state", "open", "--json", "number", "--limit", str(LIST_LIMIT)]
    assert kwargs["cwd"] == Path("/work/app")


def test_open_counts_are_zero_for_a_repo_with_nothing_open():
    cli, _ = _cli(gh_issue=(0, "[]"), gh_pr=(0, "[]"))

    assert cli.open_counts("/work/app") == OpenCounts(issues=0, prs=0)


def test_open_counts_are_none_when_gh_is_signed_out():
    cli, _ = _cli(gh_issue=(1, ""), gh_pr=(1, ""))

    assert cli.open_counts("/work/app") is None


def test_open_counts_are_none_when_gh_is_missing():
    cli, _ = _cli(gh_issue=FileNotFoundError("gh"), gh_pr=FileNotFoundError("gh"))

    assert cli.open_counts("/work/app") is None


def test_open_counts_are_none_when_gh_times_out():
    timeout = subprocess.TimeoutExpired(cmd="gh", timeout=20)
    cli, _ = _cli(gh_issue=timeout, gh_pr=timeout)

    assert cli.open_counts("/work/app") is None


def test_open_counts_are_none_when_only_one_count_can_be_read():
    cli, _ = _cli(gh_issue=(0, "[]"), gh_pr=(1, ""))

    assert cli.open_counts("/work/app") is None


def test_open_counts_are_none_when_gh_prints_something_else():
    cli, _ = _cli(gh_issue=(0, "not json"), gh_pr=(0, "[]"))

    assert cli.open_counts("/work/app") is None
