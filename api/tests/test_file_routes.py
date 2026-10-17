"""The /api/files routes: the Remote-mode gate, local-only delete, and streamed upload/download."""

import errno
import logging

import pytest
from fastapi.testclient import TestClient

from app.infra import file_drop
from app import main as app_main
from app import deps
from app.domain.pending_decisions import PendingDecisions

TOKEN = "s3cret-token-value_0123456789"


def _local():
    return TestClient(
        app_main.app,
        base_url="http://localhost",
        client=("127.0.0.1", 50000),
        headers={"X-Requested-With": "ledger"},
    )


def _phone():
    return TestClient(
        app_main.app,
        base_url="http://192.168.1.20:8501",
        client=("192.168.1.50", 5000),
        headers={"Authorization": f"Bearer {TOKEN}", "X-Requested-With": "ledger"},
    )


@pytest.fixture
def store(monkeypatch, tmp_path):
    store = PendingDecisions()
    monkeypatch.setattr(deps, "decisions", store)
    monkeypatch.setattr(deps, "access_token", TOKEN)
    monkeypatch.setenv("LEDGER_TRANSFER_DIR", str(tmp_path / "drop"))
    return store


@pytest.fixture
def remote_on(store):
    store.set_remote_mode(True)
    return store


# ------------------------------------------------------------------ the Remote-mode gate


@pytest.mark.parametrize("make_client", [_local, _phone])
@pytest.mark.parametrize(
    "method, url",
    [("get", "/api/files"), ("put", "/api/files?name=a.txt"), ("get", "/api/files/a.txt"), ("delete", "/api/files/a.txt")],
)
def test_every_file_route_is_refused_while_remote_mode_is_off(store, tmp_path, make_client, method, url):
    response = getattr(make_client(), method)(url)

    assert response.status_code == 403
    assert not (tmp_path / "drop" / "a.txt").exists()


def test_a_phone_without_the_token_is_unauthorized(remote_on):
    bare = TestClient(app_main.app, base_url="http://192.168.1.20:8501", client=("192.168.1.50", 5000))

    assert bare.get("/api/files").status_code == 401


def test_the_list_is_empty_then_shows_uploads_newest_first(remote_on):
    client = _phone()
    assert client.get("/api/files").json() == {"files": []}

    client.put("/api/files?name=first.txt", content=b"1")
    client.put("/api/files?name=second.txt", content=b"22")

    files = client.get("/api/files").json()["files"]
    assert [(f["name"], f["size"]) for f in files] == [("second.txt", 2), ("first.txt", 1)]


# ------------------------------------------------------------------ upload


def test_upload_streams_a_multi_chunk_body_to_disk(remote_on, tmp_path):
    def body():
        for _ in range(8):
            yield b"x" * 65536

    response = _phone().put("/api/files?name=video.mp4", content=body())

    assert response.status_code == 200
    assert response.json()["name"] == "video.mp4"
    assert (tmp_path / "drop" / "video.mp4").stat().st_size == 8 * 65536


def test_upload_never_overwrites_an_existing_file(remote_on, tmp_path):
    client = _phone()
    client.put("/api/files?name=photo.jpg", content=b"first")
    second = client.put("/api/files?name=photo.jpg", content=b"second").json()

    assert second["name"] == "photo (1).jpg"
    assert (tmp_path / "drop" / "photo.jpg").read_bytes() == b"first"


def test_upload_sanitizes_a_traversal_name(remote_on, tmp_path):
    response = _phone().put("/api/files", params={"name": "../../escape.txt"}, content=b"x")

    assert response.json()["name"] == "escape.txt"
    assert not (tmp_path / "escape.txt").exists()


def test_an_aborted_upload_leaves_no_file_in_the_list(remote_on, tmp_path):
    def dropped():
        yield b"partial"
        raise RuntimeError("connection lost")

    with pytest.raises(Exception):
        _phone().put("/api/files?name=big.bin", content=dropped())

    assert _phone().get("/api/files").json() == {"files": []}
    assert list((tmp_path / "drop" / file_drop.INCOMING_DIR).iterdir()) == []


def test_upload_reports_507_when_the_disk_is_full(remote_on, monkeypatch):
    def full(*_args, **_kwargs):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(file_drop.os, "link", full)

    assert _phone().put("/api/files?name=big.bin", content=b"data").status_code == 507
    assert _phone().get("/api/files").json() == {"files": []}


def test_upload_needs_a_name(remote_on):
    assert _phone().put("/api/files", content=b"x").status_code == 422


# ------------------------------------------------------------------ download


def test_download_returns_identical_bytes_as_an_attachment(remote_on):
    payload = bytes(range(256)) * 100
    _phone().put("/api/files?name=data.bin", content=payload)

    response = _phone().get("/api/files/data.bin")

    assert response.status_code == 200
    assert response.content == payload
    assert "attachment" in response.headers["content-disposition"]
    assert "data.bin" in response.headers["content-disposition"]


def test_download_supports_range_requests(remote_on):
    _phone().put("/api/files?name=data.bin", content=b"0123456789")

    response = _phone().get("/api/files/data.bin", headers={"Range": "bytes=2-4"})

    assert response.status_code == 206
    assert response.content == b"234"


def test_download_of_a_missing_file_is_404(remote_on):
    assert _phone().get("/api/files/gone.txt").status_code == 404


def test_download_cannot_leave_the_folder(remote_on, tmp_path):
    (tmp_path / "secret.txt").write_text("nope")

    assert _phone().get("/api/files/..%5Csecret.txt").status_code == 404
    assert _phone().get("/api/files/%2E%2E%2Fsecret.txt").status_code in (404, 400)


# ------------------------------------------------------------------ delete


def test_delete_from_this_machine_removes_the_file(remote_on):
    _local().put("/api/files?name=a.txt", content=b"a")

    response = _local().delete("/api/files/a.txt")

    assert response.json() == {"deleted": "a.txt"}
    assert _local().get("/api/files").json() == {"files": []}


def test_delete_from_a_phone_with_the_token_is_forbidden(remote_on, tmp_path):
    _local().put("/api/files?name=a.txt", content=b"a")

    assert _phone().delete("/api/files/a.txt").status_code == 403
    assert (tmp_path / "drop" / "a.txt").exists()


def test_delete_of_a_missing_file_is_404(remote_on):
    assert _local().delete("/api/files/gone.txt").status_code == 404


# ------------------------------------------------------------------ logging


def test_operations_are_logged_as_key_value_lines_without_contents(remote_on, caplog):
    caplog.set_level(logging.INFO, logger="ledger")
    _local().put("/api/files?name=a.txt", content=b"top secret contents")
    _local().get("/api/files/a.txt")
    _local().delete("/api/files/a.txt")

    lines = [r.getMessage() for r in caplog.records if r.name == "ledger"]
    assert "file_drop op=upload name=a.txt size=19" in lines
    assert "file_drop op=download name=a.txt" in lines
    assert "file_drop op=delete name=a.txt" in lines
    assert not any("top secret" in line for line in lines)


# ------------------------------------------------------------------ single-use download links


def _bare_phone():
    """A phone browser following a link: no token, no custom header."""
    return TestClient(app_main.app, base_url="http://192.168.1.20:8501", client=("192.168.1.50", 5000))


def _link(name="a.txt"):
    return _phone().post(f"/api/files/{name}/download-link").json()["url"]


def test_a_download_link_serves_the_file_without_the_token_once(remote_on):
    _phone().put("/api/files?name=a.txt", content=b"contents")
    url = _link()

    first = _bare_phone().get(url)
    second = _bare_phone().get(url)

    assert first.status_code == 200
    assert first.content == b"contents"
    assert "attachment" in first.headers["content-disposition"]
    assert first.headers["cache-control"] == "no-store"
    assert second.status_code == 403


def test_a_download_link_expires(remote_on, monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(deps, "download_tickets", file_drop.DownloadTickets(ttl=60, clock=lambda: clock[0]))
    _phone().put("/api/files?name=a.txt", content=b"x")
    url = _link()

    clock[0] = 61

    assert _bare_phone().get(url).status_code == 403


def test_asking_for_a_link_needs_the_token(remote_on):
    _phone().put("/api/files?name=a.txt", content=b"x")

    assert _bare_phone().post("/api/files/a.txt/download-link", headers={"X-Requested-With": "ledger"}).status_code == 401


def test_a_link_for_a_missing_file_is_404(remote_on):
    assert _phone().post("/api/files/gone.txt/download-link").status_code == 404


def test_a_download_link_does_not_open_anything_else(remote_on):
    _phone().put("/api/files?name=a.txt", content=b"x")
    ticket = _link().rsplit("/", 1)[1]
    bare = _bare_phone()

    assert bare.get("/api/files").status_code == 401
    assert bare.get(f"/api/files/{ticket}").status_code == 401
    assert bare.get(f"/api/files/download/{ticket}/more").status_code == 401
    assert bare.get("/api/meta").status_code == 401


def test_an_invented_download_link_is_refused(remote_on):
    assert _bare_phone().get("/api/files/download/" + "a" * 32).status_code == 403


def test_a_download_link_is_refused_once_remote_mode_is_off(remote_on):
    _phone().put("/api/files?name=a.txt", content=b"x")
    url = _link()

    remote_on.set_remote_mode(False)

    assert _bare_phone().get(url).status_code == 403


def test_the_ticket_is_never_logged(remote_on, caplog):
    caplog.set_level(logging.INFO, logger="ledger")
    _phone().put("/api/files?name=a.txt", content=b"x")
    url = _link()
    _bare_phone().get(url)

    ticket = url.rsplit("/", 1)[1]
    assert not any(ticket in record.getMessage() for record in caplog.records if record.name == "ledger")
