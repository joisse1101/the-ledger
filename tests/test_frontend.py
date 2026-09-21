"""Serving the built front end: assets, the single-page fallback, and the not-built message."""

import pytest
from fastapi.testclient import TestClient

import claude_db
import server
from live_snapshot import LiveSnapshot
from security import COOKIE_NAME

INDEX = "<!doctype html><title>The Ledger</title><div id=root></div>"
BUNDLE = "export const x = 1;\n" * 400  # comfortably over the gzip threshold


@pytest.fixture(autouse=True)
def _isolated(isolated_db, monkeypatch):
    monkeypatch.setattr(server, "live", LiveSnapshot(load_sessions=lambda: []))


def client(**kwargs):
    return TestClient(
        server.app,
        base_url="http://localhost",
        client=("127.0.0.1", 50000),
        headers={"X-Requested-With": "ledger"},
        **kwargs,
    )


@pytest.fixture
def dist(tmp_path, monkeypatch):
    root = tmp_path / "web" / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(INDEX, encoding="utf-8")
    (root / "assets" / "app-abc123.js").write_bytes(BUNDLE.encode())  # bytes: no newline translation on Windows
    (root / "assets" / "app-abc123.css").write_text("body{margin:0}", encoding="utf-8")
    (root / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("outside the dist folder", encoding="utf-8")
    (tmp_path / "web" / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(server, "WEB_DIST", root)
    return root


@pytest.fixture
def no_dist(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "WEB_DIST", tmp_path / "web" / "dist")


# ------------------------------------------------ with a build


@pytest.mark.parametrize("path", ["/", "/overview", "/sessions", "/sessions/aaa-1", "/projects", "/a/b/c"])
def test_page_routes_get_index_html(dist, path):
    response = client().get(path)
    assert response.status_code == 200
    assert response.text == INDEX
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-cache"


def test_an_unknown_api_path_is_a_json_404_not_the_page(dist):
    for method in ("get", "post", "delete", "put"):
        response = getattr(client(), method)("/api/nope")
        assert response.status_code == 404, method
        assert response.headers["content-type"].startswith("application/json")
        assert "The Ledger" not in response.text
    assert client().get("/api").status_code == 404
    assert client().get("/api/").status_code == 404


def test_real_api_routes_still_win_over_the_fallback(dist):
    assert "refreshed_at" in client().get("/api/meta").json()


def test_assets_are_served_with_the_right_type_and_a_long_cache(dist):
    js = client().get("/assets/app-abc123.js")
    assert js.status_code == 200
    assert js.text == BUNDLE
    assert js.headers["content-type"].split(";")[0] == "text/javascript"
    assert js.headers["cache-control"] == "public, max-age=31536000, immutable"

    css = client().get("/assets/app-abc123.css")
    assert css.headers["content-type"].split(";")[0] == "text/css"

    icon = client().get("/favicon.svg")
    assert icon.status_code == 200
    assert icon.headers["content-type"].split(";")[0] == "image/svg+xml"
    assert icon.headers["cache-control"] == "no-cache"  # not content-hashed, so revalidate


def test_a_missing_file_is_a_404_not_the_page(dist):
    for path in ("/assets/missing.js", "/nope.png", "/assets/sub/dir/x.css"):
        response = client().get(path)
        assert response.status_code == 404, path
        assert "The Ledger" not in response.text


def test_only_get_reaches_the_page(dist):
    response = client().post("/overview")
    assert response.status_code == 405
    assert response.headers["allow"] == "GET"


def test_large_assets_are_gzipped_when_the_client_accepts_it(dist):
    packed = client().get("/assets/app-abc123.js", headers={"Accept-Encoding": "gzip"})
    assert packed.headers["content-encoding"] == "gzip"
    assert packed.text == BUNDLE  # the client undoes it
    plain = client().get("/assets/app-abc123.js", headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in plain.headers


@pytest.mark.parametrize(
    "path",
    [
        "/..%2Fsecret.txt",
        "/%2e%2e/secret.txt",
        "/%2e%2e%2fsecret.txt",
        "/assets/..%2F..%2Fsecret.txt",
        "/..%5Csecret.txt",
        "/C:/Windows/win.ini",
        "/%00",
        "/assets/%00.js",
    ],
)
def test_nothing_outside_dist_is_ever_served(dist, path):
    response = client().get(path)
    assert "outside the dist folder" not in response.text
    assert "[fonts]" not in response.text  # win.ini


def test_dist_file_refuses_anything_that_resolves_outside(dist):
    assert server._dist_file("assets/app-abc123.js") == (dist / "assets" / "app-abc123.js").resolve()
    for path in ("../secret.txt", "..\\secret.txt", "assets/../../secret.txt", "../web/package.json"):
        assert server._dist_file(path) is None, path
    assert server._dist_file("assets") is None  # a directory
    assert server._dist_file("") is None


def test_the_files_are_gated_like_everything_else(dist, monkeypatch):
    monkeypatch.setattr(server, "access_token", "s3cret-token-value")
    phone = dict(base_url="http://192.168.1.20:8501", client=("192.168.1.50", 5000))
    for path in ("/", "/overview", "/assets/app-abc123.js", "/favicon.svg"):
        response = TestClient(server.app, **phone).get(path)
        assert response.status_code == 401, path
        assert "The Ledger" not in response.text and "export const" not in response.text

    signed_in = TestClient(server.app, cookies={COOKIE_NAME: "s3cret-token-value"}, **phone)
    assert signed_in.get("/overview").text == INDEX


def test_a_build_appearing_later_is_picked_up_without_a_restart(no_dist, tmp_path):
    assert client().get("/").status_code == 503
    built = tmp_path / "web" / "dist"
    built.mkdir(parents=True)
    (built / "index.html").write_text(INDEX, encoding="utf-8")
    assert client().get("/").text == INDEX


# ------------------------------------------------ without a build


def test_without_a_build_the_app_still_starts_and_explains(no_dist, monkeypatch):
    monkeypatch.setattr(claude_db, "_started", False)
    monkeypatch.setattr(claude_db.atexit, "register", lambda *a: None)
    with client() as started:
        for path in ("/", "/overview", "/sessions/aaa-1"):
            response = started.get(path)
            assert response.status_code == 503
            assert response.headers["content-type"].startswith("text/plain")
            assert "not been built" in response.text
            assert "npm run build" in response.text
        # The API is unaffected.
        assert started.get("/api/meta").json()["refreshed_at"] is not None
        assert started.get("/api/nope").status_code == 404


def test_a_dist_folder_without_index_html_counts_as_not_built(tmp_path, monkeypatch):
    empty = tmp_path / "web" / "dist"
    (empty / "assets").mkdir(parents=True)
    monkeypatch.setattr(server, "WEB_DIST", empty)
    assert not server.frontend_built()
    assert client().get("/").status_code == 503
