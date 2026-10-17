"""Remote mode: its status, switching it and the sign-in code."""

from __future__ import annotations

from app import deps
from app.infra import banner, gateway_signin
from app.services.errors import Conflict, Unavailable


def remote_mode_status() -> dict:
    """The prompt gate (`enabled`, `expires_at`) plus the lifecycle (`state`, `step`, `reason`)."""
    lifecycle = deps.remote.status() if deps.remote else {"state": "off", "step": None, "reason": None}
    return {**deps.decisions.remote_mode(), **lifecycle}


def set_enabled(enabled: bool) -> dict:
    if deps.remote is None:
        raise Unavailable("Remote mode is not available yet")
    if enabled:
        deps.remote.start()  # returns at once; clients watch the state in /api/meta
    else:
        deps.remote.stop()
    return remote_mode_status()


def sign_in_code() -> dict:
    token = deps.access_token
    if deps.remote is None or not deps.remote.is_ready() or token is None:
        raise Conflict("Remote mode is not ready")
    addresses = banner.discover_ipv4()
    if not addresses:
        raise Conflict("No network address was found for this machine")
    svg = banner.render_qr_svg(gateway_signin.signin_url(addresses[0], deps.gateway_port, token))
    if svg is None:
        raise Unavailable("QR codes are unavailable (the qrcode package is missing)")
    return {
        "svg": svg,
        "display_url": gateway_signin.display_url(addresses[0], deps.gateway_port),
        "expires_at": deps.decisions.remote_mode()["expires_at"],
    }
