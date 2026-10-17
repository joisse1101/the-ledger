"""Process-wide paths the routers rely on."""

from app import deps
from app.routers import sessions


def test_repo_root_is_the_folder_holding_api_and_hooks():
    assert (deps.REPO_ROOT / "api" / "app" / "deps.py").is_file()
    assert (deps.REPO_ROOT / "hooks").is_dir()


def test_open_repo_script_exists():
    assert sessions.OPEN_REPO_SCRIPT.is_file()
