"""POST /api/widget/workouts/open: local only, opens one fixed folder, creating it first."""

import pytest
from fastapi.testclient import TestClient

from app import deps
from app import main as app_main
from app.services import widget_service

TOKEN = "s3cret-token-value_0123456789"
URL = "/api/widget/workouts/open"


def _local():
    return TestClient(
        app_main.app, base_url="http://localhost", client=("127.0.0.1", 50000),
        headers={"X-Requested-With": "ledger"},
    )


def _phone():
    return TestClient(
        app_main.app, base_url="http://192.168.1.20:8501", client=("192.168.1.50", 5000),
        headers={"Authorization": f"Bearer {TOKEN}", "X-Requested-With": "ledger"},
    )


@pytest.fixture
def opened(tmp_path, monkeypatch):
    """A fake repo root and a fake opener that records what it is asked to open."""
    calls: list[str] = []
    monkeypatch.setattr(deps, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(deps, "access_token", TOKEN)
    monkeypatch.setattr(widget_service, "opener", calls.append)
    return calls


def test_the_folder_is_opened_and_its_path_returned(opened, tmp_path):
    folder = tmp_path / "widget" / "workouts" / "mine"
    folder.mkdir(parents=True)

    response = _local().post(URL)

    assert response.status_code == 200
    assert response.json() == {"path": str(folder)}
    assert opened == [str(folder)]


def test_a_missing_folder_is_created_before_it_is_opened(opened, tmp_path):
    folder = tmp_path / "widget" / "workouts" / "mine"
    assert not folder.exists()

    response = _local().post(URL)

    assert response.status_code == 200
    assert folder.is_dir()
    assert opened == [str(folder)]


def test_a_phone_with_the_token_is_refused_and_nothing_opens(opened, tmp_path):
    response = _phone().post(URL)

    assert response.status_code == 403
    assert opened == []
    assert not (tmp_path / "widget").exists()


def test_a_failing_opener_returns_the_path_to_open_by_hand(tmp_path, monkeypatch):
    def broken(path: str) -> None:
        raise OSError("no file manager")

    monkeypatch.setattr(deps, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(widget_service, "opener", broken)
    folder = tmp_path / "widget" / "workouts" / "mine"

    response = _local().post(URL)

    assert response.status_code == 500
    assert str(folder) in response.json()["detail"]


def test_the_personal_folder_is_the_relative_path_the_widget_uses(opened, tmp_path):
    """The widget builds `widget/workouts/mine` itself (and `.gitignore` lists it); the two must agree."""
    _local().post(URL)

    assert opened == [str(tmp_path / "widget" / "workouts" / "mine")]
    assert widget_service.PERSONAL_WORKOUTS_FOLDER == "widget/workouts/mine"
