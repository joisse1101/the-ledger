"""/api/settings: local only (even with a valid token), and an invalid folder is refused with its reason."""

import pytest
from fastapi.testclient import TestClient

from app import deps
from app import main as app_main

TOKEN = "s3cret-token-value_0123456789"


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
def api(isolated_db, write_config, monkeypatch):
    monkeypatch.setattr(deps, "access_token", TOKEN)
    write_config(isolated_db / "claude.json", {})


def test_local_read_needs_no_token(api):
    response = _local().get("/api/settings")
    assert response.status_code == 200
    assert response.json() == {"worktree_folders": [{"path": ".claude/worktrees", "built_in": True}]}


def test_local_save_needs_no_token(api, isolated_settings):
    response = _local().put("/api/settings", json={"worktree_folders": [".trees"]})
    assert response.status_code == 200
    assert response.json()["worktree_folders"][1] == {"path": ".trees", "built_in": False}
    assert isolated_settings.exists()


def test_a_phone_with_the_token_is_refused_both_ways(api, isolated_settings):
    _local().put("/api/settings", json={"worktree_folders": [".trees"]})
    saved = isolated_settings.read_bytes()

    assert _phone().get("/api/settings").status_code == 403
    assert _phone().put("/api/settings", json={"worktree_folders": []}).status_code == 403
    assert isolated_settings.read_bytes() == saved


def test_an_invalid_folder_returns_its_reason(api, isolated_settings):
    response = _local().put("/api/settings", json={"worktree_folders": ["../shared"]})
    assert response.status_code == 422
    assert "inside the repo" in response.json()["detail"]
    assert not isolated_settings.exists()
