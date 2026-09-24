"""The gateway-side sign-in banner: reads the already-provisioned token, reuses banner.py's
address discovery/QR, and prints the same content the old `--lan` banner used to."""

import pytest

import gateway_signin


# ------------------------------------------------ read_token


def test_read_token_returns_the_stored_file(tmp_path):
    (tmp_path / "token").write_text("stored-tok\n", encoding="utf-8")
    assert gateway_signin.read_token(tmp_path, {}) == "stored-tok"


def test_read_token_prefers_the_environment_variable(tmp_path):
    (tmp_path / "token").write_text("stored-tok\n", encoding="utf-8")
    assert gateway_signin.read_token(tmp_path, {"LEDGER_TOKEN": "from-env"}) == "from-env"


def test_read_token_is_none_when_nothing_is_provisioned_yet(tmp_path):
    assert gateway_signin.read_token(tmp_path, {}) is None


# ------------------------------------------------ build_signin_banner


def test_banner_lists_every_address_with_the_token_and_gateway_port():
    text = gateway_signin.build_signin_banner(
        gateway_port=10080, token="tok-123", addresses=["192.168.1.20", "10.0.0.5"]
    )
    assert "https://192.168.1.20:10080/?token=tok-123" in text
    assert "https://10.0.0.5:10080/?token=tok-123" in text
    assert "self-signed certificate" in text
    assert "network you trust" in text
    assert "plain HTTP" not in text


def test_banner_uses_the_given_gateway_port():
    text = gateway_signin.build_signin_banner(gateway_port=9999, token="tok", addresses=["10.0.0.5"])
    assert "https://10.0.0.5:9999/?token=tok" in text


def test_banner_qr_encodes_the_https_address_of_the_first_address(monkeypatch):
    encoded = []
    monkeypatch.setattr(gateway_signin.banner, "render_qr", lambda url: encoded.append(url) or "QR")
    gateway_signin.build_signin_banner(
        gateway_port=8080, token="tok", addresses=["192.168.1.20", "10.0.0.5"]
    )
    assert encoded == ["https://192.168.1.20:8080/?token=tok"]


def test_banner_says_so_when_no_address_is_found():
    text = gateway_signin.build_signin_banner(gateway_port=10080, token="tok", addresses=[])
    assert "No network address was found" in text
    assert "https://" not in text and "http://" not in text


def test_banner_discovers_addresses_when_none_are_given(monkeypatch):
    monkeypatch.setattr(gateway_signin.banner, "discover_ipv4", lambda: ["10.0.0.5"])
    text = gateway_signin.build_signin_banner(gateway_port=10080, token="tok")
    assert "https://10.0.0.5:10080/?token=tok" in text


# ------------------------------------------------ main()


def test_main_prints_a_working_link_when_the_token_exists(tmp_path, monkeypatch, capsys):
    (tmp_path / "token").write_text("tok-123\n", encoding="utf-8")
    monkeypatch.setattr(gateway_signin, "LEDGER_DIR", tmp_path)
    monkeypatch.delenv("LEDGER_TOKEN", raising=False)
    monkeypatch.delenv("GATEWAY_PORT", raising=False)
    monkeypatch.setattr(gateway_signin.banner, "discover_ipv4", lambda: ["192.168.1.20"])

    assert gateway_signin.main(["--gateway-port", "10080"]) == 0
    out = capsys.readouterr().out
    assert "https://192.168.1.20:10080/?token=tok-123" in out
    assert "http://" not in out


def test_main_defaults_the_port_from_the_gateway_port_env(tmp_path, monkeypatch, capsys):
    (tmp_path / "token").write_text("tok-123\n", encoding="utf-8")
    monkeypatch.setattr(gateway_signin, "LEDGER_DIR", tmp_path)
    monkeypatch.delenv("LEDGER_TOKEN", raising=False)
    monkeypatch.setenv("GATEWAY_PORT", "9100")
    monkeypatch.setattr(gateway_signin.banner, "discover_ipv4", lambda: ["192.168.1.20"])

    assert gateway_signin.main([]) == 0
    assert "https://192.168.1.20:9100/?token=tok-123" in capsys.readouterr().out


def test_main_fails_clearly_when_no_token_exists_yet(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gateway_signin, "LEDGER_DIR", tmp_path)
    monkeypatch.delenv("LEDGER_TOKEN", raising=False)

    assert gateway_signin.main([]) == 1
    err = capsys.readouterr().err
    assert "start the backend" in err.lower()
