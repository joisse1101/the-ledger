"""What the server prints at startup: where to open it, and how to open it from a phone."""

from __future__ import annotations

import io
import ipaddress
import socket
import sys
from typing import Iterable, Optional


def usable_ipv4(candidates: Iterable[str]) -> list[str]:
    """The addresses another device could reach: valid IPv4 only, no loopback,
    link-local (169.254.x.x) or unspecified ones, duplicates dropped, order kept."""
    seen: list[str] = []
    for candidate in candidates:
        try:
            address = ipaddress.IPv4Address(candidate)
        except ValueError:
            continue
        if address.is_loopback or address.is_link_local or address.is_unspecified:
            continue
        if str(address) not in seen:
            seen.append(str(address))
    return seen


def discover_ipv4() -> list[str]:
    """This machine's usable IPv4 addresses, the one used for outbound traffic first."""
    candidates: list[str] = []
    try:
        # Connecting a UDP socket sends nothing; it only makes the OS pick the outbound
        # interface, which is the one a phone on the same Wi-Fi/LAN can reach.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("10.255.255.255", 1))
            candidates.append(probe.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            candidates.append(str(info[4][0]))
    except OSError:
        pass
    return usable_ipv4(candidates)


def render_qr(text: str) -> Optional[str]:
    """An ASCII QR code for `text`, or None if the qrcode package or the terminal can't do it."""
    try:
        import qrcode
    except ImportError:
        return None
    qr = qrcode.QRCode(border=2)
    qr.add_data(text)
    out = io.StringIO()
    qr.print_ascii(out=out, invert=True)  # inverted: dark modules are the terminal's dark background
    rendered = out.getvalue()
    try:
        rendered.encode(sys.stdout.encoding or "ascii")
    except (UnicodeEncodeError, LookupError):
        return None  # the block characters don't exist in this terminal's encoding
    return rendered


def build_banner(*, frontend_port: int) -> str:
    """The startup text for the API process. It prints a link to the *frontend*
    rather than to itself: this process only ever serves `/api/*`, and only ever binds
    loopback — a device on the network reaches the app through the separate gateway
    (its own sign-in banner/QR is built elsewhere, from this module's discovery/QR
    helpers), not through anything printed here."""
    return "\n".join(
        [
            "",
            f"The Ledger's frontend: http://localhost:{frontend_port}/",
            "The frontend runs as its own process - start it separately: cd web && npm run preview",
            "",
        ]
    )
