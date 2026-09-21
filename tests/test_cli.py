"""The command line: which address and port the server binds, and who gets a token."""

import pytest

import banner
import server


def parse(*argv, **environ):
    return server.parse_settings(list(argv), environ)


# ------------------------------------------------ options


def test_defaults_are_local_only_on_8501():
    settings = parse()
    assert (settings.host, settings.port) == ("127.0.0.1", 8501)
    assert not settings.exposed


def test_lan_binds_every_interface():
    settings = parse("--lan")
    assert settings.host == "0.0.0.0"
    assert settings.exposed


def test_port_option():
    assert parse("--port", "9000").port == 9000


def test_an_explicit_host_beats_lan():
    settings = parse("--lan", "--host", "192.168.1.20")
    assert settings.host == "192.168.1.20"
    assert settings.exposed


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_loopback_hosts_are_not_exposed(host):
    assert not parse("--host", host).exposed


def test_environment_supplies_the_defaults():
    settings = parse(LEDGER_HOST="0.0.0.0", LEDGER_PORT="9100")
    assert (settings.host, settings.port) == ("0.0.0.0", 9100)


def test_flags_beat_the_environment():
    settings = parse("--host", "127.0.0.1", "--port", "9000", LEDGER_HOST="0.0.0.0", LEDGER_PORT="9100")
    assert (settings.host, settings.port) == ("127.0.0.1", 9000)
    # --lan too: asking for network access on the command line wins over a loopback env value.
    assert parse("--lan", LEDGER_HOST="127.0.0.1").host == "0.0.0.0"


def test_a_blank_environment_port_is_ignored():
    assert parse(LEDGER_PORT="  ").port == 8501


@pytest.mark.parametrize("argv", [["--port", "0"], ["--port", "70000"], ["--port", "eighty"]])
def test_a_bad_port_is_refused(argv, capsys):
    with pytest.raises(SystemExit):
        parse(*argv)
    assert "port" in capsys.readouterr().err


def test_a_bad_environment_port_is_refused(capsys):
    with pytest.raises(SystemExit):
        parse(LEDGER_PORT="abc")
    assert "LEDGER_PORT" in capsys.readouterr().err


# ------------------------------------------------ main()


@pytest.fixture
def launched(monkeypatch):
    """Run main() without starting a server; report what uvicorn was asked to do."""
    calls = []
    monkeypatch.setattr(server.uvicorn, "run", lambda app, **kwargs: calls.append((app, kwargs)))
    monkeypatch.setattr(server, "access_token", None)  # restored afterwards; main() assigns it
    monkeypatch.setattr(server, "provision_token", lambda: "tok-123")
    monkeypatch.setattr(server, "frontend_built", lambda: True)
    monkeypatch.setattr(banner, "discover_ipv4", lambda: ["192.168.1.20", "10.0.0.5"])
    monkeypatch.delenv("LEDGER_TOKEN", raising=False)
    return calls


def test_default_launch_is_local_with_no_access_log_and_no_token(launched, capsys):
    server.main([])

    (app, kwargs), = launched
    assert app is server.app
    assert kwargs == {"host": "127.0.0.1", "port": 8501, "access_log": False, "proxy_headers": False}
    assert server.access_token is None  # nothing to sign in with, and nothing created
    out = capsys.readouterr().out
    assert "http://localhost:8501/" in out
    assert "token" not in out.lower()


def test_lan_launch_provisions_a_token_and_prints_a_link_per_address(launched, capsys):
    server.main(["--lan", "--port", "9000"])

    (_, kwargs), = launched
    assert (kwargs["host"], kwargs["port"], kwargs["access_log"]) == ("0.0.0.0", 9000, False)
    assert server.access_token == "tok-123"
    out = capsys.readouterr().out
    assert "http://localhost:9000/" in out
    assert "http://192.168.1.20:9000/?token=tok-123" in out
    assert "http://10.0.0.5:9000/?token=tok-123" in out
    assert "plain HTTP" in out


def test_a_configured_token_is_used_even_when_local_only(launched, monkeypatch):
    monkeypatch.setenv("LEDGER_TOKEN", "from-env")
    server.main([])
    assert server.access_token == "tok-123"  # via provision_token, which honours the env var


def test_the_banner_warns_when_the_front_end_is_missing(launched, monkeypatch, capsys):
    monkeypatch.setattr(server, "frontend_built", lambda: False)
    server.main([])
    assert "npm run build" in capsys.readouterr().out
