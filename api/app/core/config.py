"""Command-line and environment settings: which address and ports the server uses."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

DEFAULT_FRONTEND_PORT = 4173  # Vite's own `vite preview` default

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8501
_LOOPBACK_BINDS = frozenset({"127.0.0.1", "localhost", "::1"})


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    frontend_port: int
    reload: bool = False

    @property
    def exposed(self) -> bool:
        """Whether devices other than this machine can connect."""
        return self.host not in _LOOPBACK_BINDS


def _parse_port(value: Optional[int], env_name: str, environ: Mapping[str, str], default: int, parser) -> int:
    port = default
    if value is not None:
        port = value
    elif environ.get(env_name, "").strip():
        try:
            port = int(environ[env_name])
        except ValueError:
            parser.error(f"{env_name} must be a number, got {environ[env_name]!r}")
    if port not in range(1, 65536):
        parser.error(f"port must be between 1 and 65535, got {port}")
    return port


def parse_settings(
    argv: Optional[Sequence[str]] = None, environ: Mapping[str, str] = os.environ
) -> Settings:
    """--host beats LEDGER_HOST beats 127.0.0.1; --port beats LEDGER_PORT beats 8501;
    --frontend-port beats LEDGER_FRONTEND_PORT beats 4173 (only used for the printed link — this
    process never connects to the frontend's port itself). `--lan` is no longer a bind mode: other
    devices now reach the app through the containerized gateway (see CLAUDE.md), so passing it exits
    with an error rather than doing anything. `--reload` has no env var (dev-only, always explicit)."""
    parser = argparse.ArgumentParser(
        prog="python -m app",
        description="The Ledger: a dashboard for your Claude Code sessions.",
    )
    parser.add_argument(
        "--lan",
        action="store_true",
        help="removed - start the containerized gateway instead (see CLAUDE.md's Setup & Run)",
    )
    parser.add_argument("--host", help=f"address to bind (default {DEFAULT_HOST}, env LEDGER_HOST)")
    parser.add_argument("--port", type=int, help=f"port to serve on (default {DEFAULT_PORT}, env LEDGER_PORT)")
    parser.add_argument(
        "--frontend-port",
        type=int,
        help=f"port the frontend is served on (default {DEFAULT_FRONTEND_PORT}, env LEDGER_FRONTEND_PORT)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="restart on code changes (dev only - imports the app fresh per restart, so this "
        "process's own startup banner/token print reflects only the very first start)",
    )
    args = parser.parse_args(argv)

    if args.lan:
        parser.error(
            "--lan has been removed: other devices connect through the containerized gateway now "
            "(see CLAUDE.md's Setup & Run), not a backend bind mode."
        )

    host = args.host or environ.get("LEDGER_HOST") or DEFAULT_HOST
    port = _parse_port(args.port, "LEDGER_PORT", environ, DEFAULT_PORT, parser)
    frontend_port = _parse_port(
        args.frontend_port, "LEDGER_FRONTEND_PORT", environ, DEFAULT_FRONTEND_PORT, parser
    )
    return Settings(host=host, port=port, frontend_port=frontend_port, reload=args.reload)
