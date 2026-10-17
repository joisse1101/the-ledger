"""Process-wide state the services share: the live registry, pending prompts, Remote mode and the token.

One module holds it so a service reads `deps.decisions` at call time and a test swaps it with
`monkeypatch.setattr(deps, "decisions", ...)`.
"""

from __future__ import annotations

import pathlib
from typing import Optional

from app.domain.live_snapshot import LiveSnapshot
from app.domain.pending_decisions import PendingDecisions
from app.infra import file_drop, remote_system
from app.infra.remote_gateway import RemoteGateway

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# The one place the live registry is read from; see LiveSnapshot.
live = LiveSnapshot()

# In-memory pending tool-permission decisions relayed from live sessions; see pending_decisions.py.
decisions = PendingDecisions()

# Remote mode's lifecycle (container runtime, web interface, gateway); built by main() or, for the
# --reload subprocess, by lifespan(). None until then; see remote_gateway.py.
remote: Optional[RemoteGateway] = None
gateway_port: int = remote_system.DEFAULT_GATEWAY_PORT

# Set by main() on every start. While None (tests that never call main()), no token
# exists, so every request that isn't plain local is refused.
access_token: Optional[str] = None

# Single-use links for downloading drop-folder files; see file_drop.DownloadTickets.
download_tickets = file_drop.DownloadTickets()


def make_remote(backend_port: int, frontend_port: int) -> RemoteGateway:
    """Remote mode's lifecycle for these ports. Reaching `ready` opens the prompt gate for other
    devices and starts its 8 hour window; turning off closes the gate again."""
    global gateway_port
    gateway_port = remote_system.gateway_port(REPO_ROOT)
    system = remote_system.RealSystem(
        repo_root=REPO_ROOT, backend_port=backend_port, frontend_port=frontend_port, gateway_port=gateway_port
    )
    return RemoteGateway(
        system,
        on_ready=lambda: decisions.set_remote_mode(True),
        on_off=lambda: decisions.set_remote_mode(False),
    )
