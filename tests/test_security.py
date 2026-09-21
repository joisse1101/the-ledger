"""Access control: who may reach the API and static files, and how a phone signs in."""

import asyncio
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import claude_db
import server
from live_snapshot import LiveSnapshot
from security import COOKIE_NAME, SecurityMiddleware, provision_token

TOKEN = "s3cret-token-value_0123456789"
HEADER = {"X-Requested-With": "ledger"}
REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _isolated(isolated_db, monkeypatch):
    monkeypatch.setattr(server, "live", LiveSnapshot(load_sessions=lambda: []))


@pytest.fixture
def token(monkeypatch):
    monkeypatch.setattr(server, "access_token", TOKEN)
    return TOKEN


def remote(**kwargs):
    """A phone on the LAN: a non-loopback client addressing the machine by its LAN IP."""
    kwargs.setdefault("base_url", "http://192.168.1.20:8501")
    return TestClient(server.app, client=("192.168.1.50", 5000), follow_redirects=False, **kwargs)


def local(host="localhost", client="127.0.0.1", headers=None, **kwargs):
    # `host` goes in the Host header itself, so values httpx would reject in a URL still get sent.
    return TestClient(
        server.app,
        base_url="http://localhost",
        client=(client, 50000),
        follow_redirects=False,
        headers={"Host": host, **(headers or {})},
        **kwargs,
    )


# ------------------------------------------------ 4.1: who needs the token


@pytest.mark.parametrize("path", ["/api/meta", "/api/transcripts", "/api/live", "/", "/assets/x.js"])
def test_a_remote_request_without_the_token_gets_401_and_no_data(token, path):
    response = remote().get(path)
    assert response.status_code == 401
    assert "printed" in response.text  # points at the address printed at startup
    assert "refreshed_at" not in response.text and "sessions" not in response.text


def test_a_wrong_token_is_refused_however_it_is_presented(token):
    assert remote().get("/api/meta", params={"token": "wrong"}).status_code == 401
    assert remote(cookies={COOKIE_NAME: "wrong"}).get("/api/meta").status_code == 401
    assert remote().get("/api/meta", headers={"Authorization": "Bearer wrong"}).status_code == 401
    # A token that differs only in length or in non-ASCII must not crash the comparison.
    assert remote().get("/api/meta", params={"token": TOKEN + "x"}).status_code == 401
    assert remote().get("/api/meta", params={"token": "é"}).status_code == 401


@pytest.mark.parametrize(
    "header",
    [{"Forwarded": "for=203.0.113.9"}, {"X-Forwarded-For": "203.0.113.9"}, {"X-Real-IP": "203.0.113.9"}],
)
def test_a_request_forwarded_from_loopback_needs_the_token(token, header):
    proxied = local(headers=header)
    assert proxied.get("/api/meta").status_code == 401
    assert proxied.get("/api/meta", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200


def test_the_cookie_and_the_bearer_header_are_accepted(token):
    assert remote(cookies={COOKIE_NAME: TOKEN}).get("/api/meta").status_code == 200
    assert remote().get("/api/meta", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200
    assert remote().get("/api/meta", headers={"Authorization": f"bearer {TOKEN}"}).status_code == 200


def test_a_token_in_the_query_authorises_a_request_that_cannot_be_redirected(token):
    response = remote().post("/api/refresh", params={"token": TOKEN}, headers=HEADER)
    assert response.status_code == 200
    assert "location" not in response.headers


@pytest.mark.parametrize("client", ["127.0.0.1", "::1", "::ffff:127.0.0.1"])
def test_plain_loopback_needs_no_token(token, client):
    assert local(client=client).get("/api/meta").status_code == 200


def test_loopback_needs_no_token_even_when_none_is_configured():
    assert local().get("/api/meta").status_code == 200


def test_with_no_token_configured_nothing_remote_gets_in():
    assert server.access_token is None
    assert remote().get("/api/meta").status_code == 401
    assert remote().get("/api/meta", params={"token": ""}).status_code == 401
    assert remote(cookies={COOKIE_NAME: ""}).get("/api/meta").status_code == 401


def test_the_default_test_client_is_not_local():
    # Starlette's own TestClient identifies as host "testclient": not loopback, so refused.
    assert TestClient(server.app).get("/api/meta").status_code == 401


def test_a_request_with_no_client_address_is_not_local():
    async def app(scope, receive, send):
        raise AssertionError("must not be reached")

    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/meta",
        "query_string": b"",
        "headers": [(b"host", b"localhost")],
        "client": None,
    }
    asyncio.run(SecurityMiddleware(app, token=lambda: None)(scope, receive, send))
    assert sent[0]["status"] == 401


def test_websockets_are_refused(token):
    with pytest.raises(WebSocketDisconnect):
        with remote(cookies={COOKIE_NAME: TOKEN}).websocket_connect("/ws"):
            pass


def _seed_finished_session(isolated_db, write_config, write_transcript):
    folder = isolated_db / "projects" / "-h-alpha"
    transcript = folder / "aaa-1.jsonl"
    write_config(isolated_db / "claude.json", {"/h/alpha": {}})
    write_transcript(
        transcript,
        [{"type": "user", "timestamp": "2024-01-01T00:00:00Z", "cwd": "/h/alpha", "sessionId": "aaa-1",
          "message": {"content": "hi"}}],
    )
    claude_db.refresh()
    return transcript


def test_a_remote_delete_without_the_token_is_refused_and_deletes_nothing(
    token, isolated_db, write_config, write_transcript
):
    transcript = _seed_finished_session(isolated_db, write_config, write_transcript)

    # The custom header is present, so it is the missing token that stops this.
    response = remote().delete("/api/sessions/aaa-1", headers=HEADER)
    assert response.status_code == 401
    assert transcript.exists()
    assert remote().delete("/api/projects", params={"path": "/h/alpha"}, headers=HEADER).status_code == 401
    assert transcript.exists()

    # And without the header either: still 401, the token check comes first.
    assert remote().delete("/api/sessions/aaa-1").status_code == 401
    assert transcript.exists()

    # Signed in, the same request goes through.
    signed_in = remote(cookies={COOKIE_NAME: TOKEN})
    assert signed_in.delete("/api/sessions/aaa-1", headers=HEADER).status_code == 200
    assert not transcript.exists()


# ------------------------------------------------ 4.2: signing in with a link


def test_a_valid_token_redirects_to_the_same_url_without_it_and_sets_the_cookie(token):
    response = remote().get("/api/meta", params={"token": TOKEN})
    assert response.status_code == 303
    assert response.headers["location"] == "/api/meta"
    assert TOKEN not in response.headers["location"]

    cookie = response.headers["set-cookie"]
    attributes = [part.strip().lower() for part in cookie.split(";")]
    assert attributes[0] == f"{COOKIE_NAME}={TOKEN}".lower()
    assert "httponly" in attributes
    # Lax: a link from a QR scanner is a cross-site navigation, and Strict would keep
    # the cookie off the very redirect that lands the user on the page.
    assert "samesite=lax" in attributes
    assert "path=/" in attributes
    assert "max-age=31536000" in attributes
    assert "secure" not in attributes  # plain HTTP on a LAN


def test_the_redirect_keeps_every_other_query_parameter(token):
    response = remote().get(
        "/api/transcripts", params=[("q", "a b"), ("project", "x"), ("token", TOKEN), ("project", "y"), ("limit", "5")]
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/api/transcripts?q=a+b&project=x&project=y&limit=5"


def test_the_root_url_redirects_to_the_root(token):
    response = remote().get("/", params={"token": TOKEN})
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_the_redirect_cannot_point_at_another_site(token):
    # A full URL: a bare "//evil.example/x" would be read by the client as a host, not a path.
    response = remote().get("http://192.168.1.20:8501//evil.example/x", params={"token": TOKEN})
    assert response.status_code == 303
    assert not response.headers["location"].startswith("//")
    assert response.headers["location"] == "/evil.example/x"


def test_a_wrong_token_neither_redirects_nor_sets_a_cookie(token):
    response = remote().get("/api/meta", params={"token": "wrong"})
    assert response.status_code == 401
    assert "location" not in response.headers
    assert "set-cookie" not in response.headers


def test_a_signed_in_device_that_opens_the_link_again_still_loses_the_token_from_the_address(token):
    response = remote(cookies={COOKIE_NAME: TOKEN}).get("/api/meta", params={"token": TOKEN})
    assert response.status_code == 303


def test_after_the_redirect_the_cookie_alone_is_enough(token):
    with remote() as phone:
        first = phone.get("/api/meta", params={"token": TOKEN})
        assert first.status_code == 303
        # The client's cookie jar now holds what Set-Cookie sent; nothing else is attached.
        followed = phone.get(first.headers["location"])
        assert followed.status_code == 200
        assert "refreshed_at" in followed.json()
        assert "token" not in str(followed.request.url)

    # A different browser with only that cookie value is accepted as well.
    assert remote(cookies={COOKIE_NAME: TOKEN}).get("/api/meta").status_code == 200


def test_a_changed_token_signs_the_old_cookie_out(monkeypatch):
    monkeypatch.setattr(server, "access_token", "new-token-value")
    assert remote(cookies={COOKIE_NAME: TOKEN}).get("/api/meta").status_code == 401


def test_a_token_with_cookie_special_characters_round_trips(monkeypatch):
    odd = 'pa ss;wo"rd,1=2'
    monkeypatch.setattr(server, "access_token", odd)
    with remote() as phone:
        first = phone.get("/api/meta", params={"token": odd})
        assert first.status_code == 303
        assert phone.get("/api/meta").status_code == 200


# ------------------------------------------------ 4.3: token provisioning


def test_provisioning_generates_once_and_reuses_it(tmp_path):
    directory = tmp_path / ".ledger"
    first = provision_token(directory, environ={})
    second = provision_token(directory, environ={})
    assert first == second
    assert len(first) >= 43  # 32 random bytes, urlsafe-base64: at least 128 bits
    assert (directory / "token").read_text(encoding="utf-8").strip() == first


def test_the_environment_setting_wins_and_creates_no_file(tmp_path):
    directory = tmp_path / ".ledger"
    assert provision_token(directory, environ={"LEDGER_TOKEN": "from-env"}) == "from-env"
    assert not directory.exists()

    provision_token(directory, environ={})  # a stored token exists now
    assert provision_token(directory, environ={"LEDGER_TOKEN": "from-env"}) == "from-env"


def test_a_blank_environment_setting_is_ignored(tmp_path):
    token = provision_token(tmp_path / ".ledger", environ={"LEDGER_TOKEN": "   "})
    assert token.strip() and token != "   "


def test_deleting_the_stored_token_replaces_it(tmp_path):
    directory = tmp_path / ".ledger"
    first = provision_token(directory, environ={})
    (directory / "token").unlink()
    assert provision_token(directory, environ={}) != first


def test_an_empty_token_file_is_regenerated(tmp_path):
    directory = tmp_path / ".ledger"
    directory.mkdir()
    (directory / "token").write_text("\n", encoding="utf-8")
    assert provision_token(directory, environ={}).strip()


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_git_ignores_the_stored_token():
    result = subprocess.run(
        ["git", "check-ignore", ".ledger/token"], cwd=REPO, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ".ledger/token"


# ------------------------------------------------ 4.4: cross-site and rebinding guards


@pytest.mark.parametrize("method", ["post", "delete", "put", "patch"])
def test_a_state_changing_request_needs_the_custom_header(method):
    client = local()
    assert getattr(client, method)("/api/refresh").status_code == 403


def test_refresh_needs_the_header_and_works_with_it():
    assert local().post("/api/refresh").status_code == 403
    assert local().post("/api/refresh", headers=HEADER).status_code == 200
    assert local().post("/api/refresh", headers={"X-Requested-With": "other"}).status_code == 403


def test_a_get_needs_no_custom_header():
    assert local().get("/api/meta").status_code == 200


def test_the_custom_header_is_required_of_signed_in_devices_too(token):
    phone = remote(cookies={COOKIE_NAME: TOKEN})
    assert phone.post("/api/refresh").status_code == 403
    assert phone.post("/api/refresh", headers=HEADER).status_code == 200


def test_a_cross_site_delete_without_the_header_deletes_nothing(isolated_db, write_config, write_transcript):
    transcript = _seed_finished_session(isolated_db, write_config, write_transcript)
    # What a form or fetch from another site can send: no custom header.
    assert local().delete("/api/sessions/aaa-1").status_code == 403
    assert transcript.exists()


@pytest.mark.parametrize(
    "host",
    ["evil.example", "localhost.evil.example", "127.0.0.1.evil.example", "localhost:abc", "0.0.0.0:8501"],
)
def test_loopback_with_another_host_name_is_refused(host):
    assert local(host=host).get("/api/meta").status_code == 403


@pytest.mark.parametrize("host", ["localhost", "localhost:9000", "LOCALHOST:8501", "127.0.0.1:8501", "[::1]:8501"])
def test_loopback_host_names_are_accepted_with_or_without_a_port(host):
    assert local(host=host).get("/api/meta").status_code == 200


@pytest.mark.parametrize("path", ["/api/meta", "/api/nope", "/", "/api/refresh"])
def test_no_response_carries_a_cors_header(token, path):
    origin = {"Origin": "https://evil.example"}
    responses = [
        local().get(path, headers=origin),
        local().post(path, headers={**origin, **HEADER}),
        local().options(
            path, headers={**origin, "Access-Control-Request-Method": "DELETE", "Access-Control-Request-Headers": "x-requested-with"}
        ),
        remote().get(path, headers=origin),  # 401
        remote(cookies={COOKIE_NAME: TOKEN}).get(path, headers=origin),
        remote().options(path, headers={**origin, "Access-Control-Request-Method": "GET"}),
        local(host="evil.example").get(path, headers=origin),  # 403
    ]
    for response in responses:
        assert not [h for h in response.headers if h.lower().startswith("access-control-")], response


def test_a_preflight_for_a_delete_is_never_approved():
    response = local().options(
        "/api/sessions/aaa-1",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "x-requested-with",
        },
    )
    assert not response.is_success
    assert "access-control-allow-origin" not in response.headers
