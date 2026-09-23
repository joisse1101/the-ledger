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


def build_banner(
    *,
    frontend_port: int,
    lan_addresses: Optional[list[str]] = None,
    token: Optional[str] = None,
    qr: Optional[str] = None,
) -> str:
    """The startup text for the API process. It prints a link to the *frontend*
    rather than to itself: this process only ever serves `/api/*`. `lan_addresses` is None
    when the API is local-only."""
    lines = ["", f"The Ledger's frontend: http://localhost:{frontend_port}/"]
    preview_command = "cd web && npm run preview" + (" -- --host" if lan_addresses is not None else "")
    lines.append(f"The frontend runs as its own process - start it separately: {preview_command}")

    if lan_addresses is not None:
        lines.append("")
        if lan_addresses and token:
            lines.append("Open on another device (the link signs that device in):")
            lines += [f"  http://{address}:{frontend_port}/?token={token}" for address in lan_addresses]
            if qr:
                lines += ["", f"Scan to open {lan_addresses[0]}:", qr.rstrip("\n")]
        else:
            lines.append("No network address was found for this machine.")
        lines += [
            "",
            "This is plain HTTP: the token only keeps out devices that don't have it, and anyone",
            "who can watch this network can read it. Use --lan on networks you trust.",
            "If a phone can't connect, allow Python through the firewall (on Windows: allow it",
            "on Private networks) and check the phone is on the same network.",
        ]

    lines.append("")
    return "\n".join(lines)
