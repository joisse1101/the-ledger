import pytest
from fastapi.testclient import TestClient

import claude_db
import server
from live_snapshot import LiveSnapshot


def _client():
    """A client the security middleware treats as the browser on this machine."""
    return TestClient(
        server.app,
        base_url="http://localhost",
        client=("127.0.0.1", 50000),
        headers={"X-Requested-With": "ledger"},
    )


@pytest.fixture
def client(isolated_db):
    return _client()


def test_meta_has_refreshed_at_field(client):
    response = client.get("/api/meta")
    assert response.status_code == 200
    assert "refreshed_at" in response.json()


def test_meta_reports_the_snapshot_timestamp(client):
    stamp = claude_db.refresh()
    assert client.get("/api/meta").json()["refreshed_at"] == stamp.isoformat()


def test_refresh_endpoint_advances_refreshed_at(client):
    first = client.post("/api/refresh").json()["refreshed_at"]
    second = client.post("/api/refresh").json()["refreshed_at"]
    assert second > first
    assert client.get("/api/meta").json()["refreshed_at"] == second


def test_concurrent_refreshes_run_one_after_the_other(monkeypatch):
    import threading
    import time
    from datetime import datetime

    active = 0
    max_active = 0
    guard = threading.Lock()

    def slow_refresh():
        nonlocal active, max_active
        with guard:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with guard:
            active -= 1
        return datetime.now()

    monkeypatch.setattr(claude_db, "refresh", slow_refresh)
    threads = [threading.Thread(target=server.locked_refresh) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert max_active == 1


def test_refresh_loop_calls_refresh_again_after_each_interval(monkeypatch):
    import asyncio

    calls = []
    monkeypatch.setattr(server, "locked_refresh", lambda: calls.append(1))

    async def run():
        task = asyncio.create_task(server.refresh_loop(0.01))
        await asyncio.sleep(0.15)
        task.cancel()

    asyncio.run(run())
    assert len(calls) >= 2


def test_refresh_loop_survives_a_failed_scan(monkeypatch):
    import asyncio

    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("disk hiccup")

    monkeypatch.setattr(server, "locked_refresh", flaky)

    async def run():
        task = asyncio.create_task(server.refresh_loop(0.01))
        await asyncio.sleep(0.15)
        task.cancel()

    asyncio.run(run())
    assert len(calls) >= 2


def test_lifespan_seeds_the_snapshot(isolated_db, monkeypatch):
    monkeypatch.setattr(claude_db, "_started", False)
    monkeypatch.setattr(claude_db.atexit, "register", lambda *a: None)
    with _client() as started:
        assert started.get("/api/meta").json()["refreshed_at"] is not None
