"""The startup banner: address discovery, the QR code and the text."""

import types

import banner

# ------------------------------------------------ address filter


def test_usable_ipv4_drops_loopback_link_local_unspecified_and_junk():
    candidates = [
        "127.0.0.1",
        "127.5.5.5",
        "169.254.10.2",
        "192.168.1.20",
        "0.0.0.0",
        "::1",
        "fe80::1",
        "not-an-ip",
        "",
        "10.0.0.5",
        "192.168.1.20",  # duplicate
        "172.16.0.9",
    ]
    assert banner.usable_ipv4(candidates) == ["192.168.1.20", "10.0.0.5", "172.16.0.9"]


def test_usable_ipv4_of_nothing_is_empty():
    assert banner.usable_ipv4([]) == []
    assert banner.usable_ipv4(["127.0.0.1", "169.254.1.1"]) == []


class _Probe:
    """Stands in for the UDP socket: it 'connects' and reports the outbound address."""

    def __init__(self, *args):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def connect(self, address):
        pass

    def getsockname(self):
        return ("192.168.1.20", 54321)


def test_discovery_puts_the_outbound_interface_first_and_filters_the_rest(monkeypatch):
    monkeypatch.setattr(banner.socket, "socket", _Probe)
    monkeypatch.setattr(banner.socket, "gethostname", lambda: "box")
    monkeypatch.setattr(
        banner.socket,
        "getaddrinfo",
        lambda *args: [
            (2, 1, 6, "", ("169.254.3.4", 0)),
            (2, 1, 6, "", ("10.0.0.5", 0)),
            (2, 1, 6, "", ("192.168.1.20", 0)),
            (2, 1, 6, "", ("127.0.0.1", 0)),
        ],
    )
    assert banner.discover_ipv4() == ["192.168.1.20", "10.0.0.5"]


def test_discovery_survives_a_machine_with_no_network(monkeypatch):
    def offline(*args, **kwargs):
        raise OSError("network is unreachable")

    monkeypatch.setattr(banner.socket, "socket", offline)
    monkeypatch.setattr(banner.socket, "gethostname", lambda: "box")
    monkeypatch.setattr(banner.socket, "getaddrinfo", offline)
    assert banner.discover_ipv4() == []


# ------------------------------------------------ QR


def test_render_qr_is_a_block_of_lines(monkeypatch):
    monkeypatch.setattr(banner.sys, "stdout", types.SimpleNamespace(encoding="utf-8"))
    rendered = banner.render_qr("http://192.168.1.20:8501/?token=abc")
    lines = rendered.splitlines()
    assert len(lines) > 10
    assert len({len(line) for line in lines}) == 1  # rectangular
    assert any(char in rendered for char in "█▀▄")


def test_render_qr_steps_aside_when_the_terminal_cannot_show_it(monkeypatch):
    monkeypatch.setattr(banner.sys, "stdout", types.SimpleNamespace(encoding="ascii"))
    assert banner.render_qr("http://192.168.1.20:8501/") is None


# ------------------------------------------------ text


def test_local_only_banner_has_one_address_no_token_talk_and_the_preview_reminder():
    text = banner.build_banner(frontend_port=8501)
    assert "http://localhost:8501/" in text
    assert "token" not in text.lower()
    assert "HTTP" not in text
    assert "npm run preview" in text and "--host" not in text


def test_banner_uses_the_given_frontend_port():
    text = banner.build_banner(frontend_port=9000)
    assert "http://localhost:9000/" in text
