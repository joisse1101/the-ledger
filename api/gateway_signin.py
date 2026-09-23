"""Prints the gateway's sign-in link/QR for every device on this network.

The backend no longer knows it's reachable over the network (see `server.py`'s dropped `--lan`),
so this is invoked separately, once the gateway container is up, to tell the user how to reach it
from a phone. It reads the token the backend has already provisioned (`api/.ledger/token`, via the
same `LEDGER_TOKEN`/stored-file precedence as `security.provision_token`) rather than provisioning
one itself, and reuses `banner.discover_ipv4()`/`banner.render_qr()` so address-discovery logic
lives in exactly one place.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Mapping, Optional, Sequence

import banner
from security import LEDGER_DIR, TOKEN_ENV

DEFAULT_GATEWAY_PORT = 10080  # matches gateway/docker-compose.yml's GATEWAY_PORT default


def read_token(directory=LEDGER_DIR, environ: Mapping[str, str] = os.environ) -> Optional[str]:
    """The already-provisioned token, or None if the backend hasn't started yet."""
    configured = environ.get(TOKEN_ENV, "").strip()
    if configured:
        return configured
    try:
        stored = (directory / "token").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return stored or None


def build_signin_banner(
    *, gateway_port: int, token: str, addresses: Optional[list[str]] = None
) -> str:
    """Same content as the backend's old `--lan` banner, just built from the gateway side."""
    if addresses is None:
        addresses = banner.discover_ipv4()

    lines = [""]
    if addresses:
        lines.append("Open on another device (the link signs that device in):")
        lines += [f"  http://{address}:{gateway_port}/?token={token}" for address in addresses]
        qr = banner.render_qr(f"http://{addresses[0]}:{gateway_port}/?token={token}")
        if qr:
            lines += ["", f"Scan to open {addresses[0]}:", qr.rstrip("\n")]
    else:
        lines.append("No network address was found for this machine.")
    lines += [
        "",
        "This is plain HTTP: the token only keeps out devices that don't have it, and anyone",
        "who can watch this network can read it. Only start the gateway on a network you trust.",
        "If a phone can't connect, allow the gateway's port through Windows Firewall and check",
        "the phone is on the same network.",
        "",
    ]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python gateway_signin.py",
        description="Print the gateway's sign-in link and QR code for every device on this network.",
    )
    parser.add_argument(
        "--gateway-port",
        type=int,
        default=int(os.environ.get("GATEWAY_PORT", DEFAULT_GATEWAY_PORT)),
        help=f"port the gateway is published on (default {DEFAULT_GATEWAY_PORT}, env GATEWAY_PORT)",
    )
    args = parser.parse_args(argv)

    token = read_token(LEDGER_DIR)
    if token is None:
        print(
            "No access token found yet - start the backend first (python server.py), "
            "then run this again.",
            file=sys.stderr,
        )
        return 1

    print(build_signin_banner(gateway_port=args.gateway_port, token=token), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
