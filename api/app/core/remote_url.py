"""A git remote URL turned into the repo's web page, and the host's display name. Pure string work."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

GITHUB_HOST = "github.com"
GITHUB_LABEL = "GitHub"
_URL_SCHEMES = {"http", "https", "ssh", "git"}
# `git@host:owner/repo.git`. The host must contain a dot so a Windows path like `C:/repo` is not one.
_SCP_REMOTE = re.compile(r"^(?:[\w.-]+@)?(?P<host>[\w-]+(?:\.[\w-]+)+):(?!//)(?P<path>[\w./-]+)$")


def _repo_page(host: str, path: str) -> Optional[str]:
    path = path.strip("/").removesuffix(".git")
    if not path:
        return None
    return f"https://{host.lower()}/{path}"


def web_url(remote: str) -> Optional[str]:
    """The https page of the repo behind `remote`, or None for a local path or anything else that
    is not a hosted remote. Credentials, the port and a `.git` suffix are dropped."""
    remote = remote.strip()
    scp = _SCP_REMOTE.match(remote)
    if scp:
        return _repo_page(scp["host"], scp["path"])
    parsed = urlparse(remote)
    if parsed.scheme not in _URL_SCHEMES or not parsed.hostname:
        return None
    return _repo_page(parsed.hostname, parsed.path)


def host_label(url: str) -> str:
    """"GitHub" for github.com, otherwise the hostname as it is."""
    host = urlparse(url).hostname or ""
    return GITHUB_LABEL if host == GITHUB_HOST else host
