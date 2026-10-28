"""ProjectRepoLookup with a fake RepoCli and clock: what it resolves, caches and survives."""

from app.infra.repo_cli import OpenCounts
from app.domain.project_repo import ProjectRepo
from app.services.project_repo_service import CACHE_TTL_SECONDS, FAILURE_TTL_SECONDS, ProjectRepoLookup


class FakeCli:
    def __init__(self, remotes, counts=None):
        self.remotes = remotes
        self.counts = counts or {}
        self.remote_calls: list[str] = []
        self.count_calls: list[str] = []

    def remote_url(self, path):
        self.remote_calls.append(path)
        remote = self.remotes.get(path)
        if isinstance(remote, BaseException):
            raise remote
        return remote

    def open_counts(self, path):
        self.count_calls.append(path)
        return self.counts.get(path)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _lookup(cli, clock=None):
    return ProjectRepoLookup(cli, clock=clock or Clock())


def test_a_github_project_gets_its_link_and_counts():
    cli = FakeCli({"/app": "git@github.com:acme/app.git"}, {"/app": OpenCounts(issues=7, prs=2)})

    assert _lookup(cli).lookup_all(["/app"]) == [
        ProjectRepo(path="/app", host="GitHub", url="https://github.com/acme/app", issues=7, prs=2)
    ]


def test_another_host_keeps_its_link_and_never_runs_gh():
    cli = FakeCli({"/app": "git@gitlab.com:acme/app.git"})

    [repo] = _lookup(cli).lookup_all(["/app"])

    assert (repo.host, repo.url, repo.issues, repo.prs) == ("gitlab.com", "https://gitlab.com/acme/app", None, None)
    assert cli.count_calls == []


def test_a_project_without_a_remote_has_nothing():
    cli = FakeCli({})

    [repo] = _lookup(cli).lookup_all(["/app"])

    assert (repo.host, repo.url, repo.issues, repo.prs) == (None, None, None, None)
    assert cli.count_calls == []


def test_a_local_path_remote_counts_as_no_remote():
    cli = FakeCli({"/app": "/srv/git/app.git"})

    [repo] = _lookup(cli).lookup_all(["/app"])

    assert repo.url is None


def test_unreadable_counts_keep_the_link():
    cli = FakeCli({"/app": "https://github.com/acme/app.git"})

    [repo] = _lookup(cli).lookup_all(["/app"])

    assert (repo.url, repo.issues, repo.prs) == ("https://github.com/acme/app", None, None)


def test_results_follow_the_order_of_the_paths():
    cli = FakeCli({"/a": "https://gitlab.com/x/a", "/b": "https://gitlab.com/x/b", "/c": "https://gitlab.com/x/c"})

    repos = _lookup(cli).lookup_all(["/c", "/a", "/b"])

    assert [r.path for r in repos] == ["/c", "/a", "/b"]


def test_no_paths_means_no_work():
    assert _lookup(FakeCli({})).lookup_all([]) == []


def test_a_recent_lookup_is_served_from_the_cache():
    clock = Clock()
    cli = FakeCli({"/app": "https://github.com/acme/app"}, {"/app": OpenCounts(1, 1)})
    lookup = _lookup(cli, clock)
    lookup.lookup_all(["/app"])

    clock.now += CACHE_TTL_SECONDS - 1
    lookup.lookup_all(["/app"])

    assert cli.remote_calls == ["/app"]


def test_an_expired_lookup_is_read_again():
    clock = Clock()
    cli = FakeCli({"/app": "https://github.com/acme/app"}, {"/app": OpenCounts(1, 1)})
    lookup = _lookup(cli, clock)
    lookup.lookup_all(["/app"])

    clock.now += CACHE_TTL_SECONDS + 1
    lookup.lookup_all(["/app"])

    assert cli.remote_calls == ["/app", "/app"]


def test_an_incomplete_lookup_is_retried_sooner_and_picks_up_the_fix():
    clock = Clock()
    cli = FakeCli({"/app": "https://github.com/acme/app"})
    lookup = _lookup(cli, clock)
    assert lookup.lookup_all(["/app"])[0].issues is None

    cli.counts["/app"] = OpenCounts(issues=3, prs=0)  # the user ran `gh auth login`
    clock.now += FAILURE_TTL_SECONDS + 1

    assert lookup.lookup_all(["/app"])[0].issues == 3


def test_an_incomplete_lookup_is_not_repeated_on_every_call():
    cli = FakeCli({"/app": "https://github.com/acme/app"})
    lookup = _lookup(cli)

    lookup.lookup_all(["/app"])
    lookup.lookup_all(["/app"])

    assert cli.count_calls == ["/app"]


def test_one_project_failing_does_not_affect_the_others():
    cli = FakeCli(
        {"/bad": None, "/good": "https://github.com/acme/app"},
        {"/good": OpenCounts(issues=4, prs=1)},
    )

    bad, good = _lookup(cli).lookup_all(["/bad", "/good"])

    assert bad.url is None
    assert (good.issues, good.prs) == (4, 1)
