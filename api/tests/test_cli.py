"""The command line: which address and port the server binds, and who gets a token."""

import pytest

from app import cli
from app import main as app_main
from app.core.config import parse_settings
from app import deps


def parse(*argv, **environ):
    return parse_settings(list(argv), environ)


# ------------------------------------------------ options


def test_defaults_are_local_only_on_8501():
    settings = parse()
    assert (settings.host, settings.port, settings.frontend_port) == ("127.0.0.1", 8501, 8502)
    assert not settings.exposed


def test_lan_is_no_longer_a_bind_mode_and_exits_with_an_error(capsys):
    with pytest.raises(SystemExit):
        parse("--lan")
    err = capsys.readouterr().err
    assert "--lan" in err
    assert "gateway" in err.lower()


def test_lan_errors_even_alongside_other_options(capsys):
    with pytest.raises(SystemExit):
        parse("--lan", "--host", "192.168.1.20")
    assert "gateway" in capsys.readouterr().err.lower()


def test_port_option():
    assert parse("--port", "9000").port == 9000


def test_frontend_port_option_and_env():
    assert parse("--frontend-port", "5000").frontend_port == 5000
    assert parse(LEDGER_FRONTEND_PORT="5001").frontend_port == 5001
    assert parse("--frontend-port", "5000", LEDGER_FRONTEND_PORT="5001").frontend_port == 5000


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_loopback_hosts_are_not_exposed(host):
    assert not parse("--host", host).exposed


def test_environment_supplies_the_defaults():
    settings = parse(LEDGER_HOST="0.0.0.0", LEDGER_PORT="9100")
    assert (settings.host, settings.port) == ("0.0.0.0", 9100)


def test_flags_beat_the_environment():
    settings = parse("--host", "127.0.0.1", "--port", "9000", LEDGER_HOST="0.0.0.0", LEDGER_PORT="9100")
    assert (settings.host, settings.port) == ("127.0.0.1", 9000)


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
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **kwargs: calls.append((app, kwargs)))
    monkeypatch.setattr(deps, "access_token", None)  # restored afterwards
    yield calls


def test_default_launch_is_local_with_no_access_log_and_no_token(launched, capsys):
    cli.main([])

    (app, kwargs), = launched
    assert app is app_main.app
    assert kwargs == {"host": "127.0.0.1", "port": 8501, "access_log": False, "proxy_headers": False}
    # The token belongs to a Remote mode session, so none exists at launch.
    assert deps.access_token is None
    out = capsys.readouterr().out
    assert "http://localhost:8502/" in out  # the frontend's default port, not the API's
    assert "token" not in out.lower()  # nothing about network sign-in is printed here anymore


def test_a_custom_port_and_frontend_port_are_passed_through(launched, capsys):
    cli.main(["--port", "9000", "--frontend-port", "5000"])

    (_, kwargs), = launched
    assert (kwargs["host"], kwargs["port"], kwargs["access_log"]) == ("127.0.0.1", 9000, False)
    assert "http://localhost:5000/" in capsys.readouterr().out


def test_reload_passes_an_import_string_not_the_app_object(launched):
    # uvicorn only actually reloads when given an import string, so the reload branch can't reuse
    # the app object - that branch is exercised by
    # test_default_launch_is_local_with_no_access_log_and_no_token above.
    cli.main(["--reload"])

    (app, kwargs), = launched
    assert app == "app.main:app"
    assert kwargs == {
        "host": "127.0.0.1",
        "port": 8501,
        "reload": True,
        "access_log": False,
        "proxy_headers": False,
    }
