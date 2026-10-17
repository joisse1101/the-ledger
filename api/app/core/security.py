"""Access control for the API: one ASGI middleware over every request.

A request is *local* only when it comes from a loopback address and carries no
proxy marker (a tunnel or reverse proxy on this machine also connects from
loopback). Local requests need no token but must name a loopback host, so a web
page can't reach the app by rebinding its own DNS name to 127.0.0.1. Everything
else must present the access token as `Authorization: Bearer <token>` — the
frontend (always same-origin with the API, via its own dev/preview proxy or the
gateway) is what turns a sign-in link's `?token=` into that header; the API itself
has no query or cookie handling for it. The token exists only while Remote mode is
on (see `deps.make_remote`); with none, every non-local request is refused. State-changing requests must also carry a
custom header, which a page on another site can't add without a CORS preflight —
and with no `CORSMiddleware` registered at all, every such preflight fails.
"""

from __future__ import annotations

import hmac
import re
import secrets
from typing import Callable, Optional

from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "ledger"

LOOPBACK_CLIENTS = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1"})
FORWARD_HEADERS = ("forwarded", "x-forwarded-for", "x-real-ip")
# The one address that works without the bearer token: a file-drop download link. The ticket in the
# path is the credential (single-use, expires in a minute) and the route redeems it; this is only
# the shape match that lets the request reach that route.
_DOWNLOAD_LINK = re.compile(r"^/api/files/download/[A-Za-z0-9_-]{16,128}$")
_LOOPBACK_HOST = re.compile(r"^(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?$", re.IGNORECASE)

UNAUTHORIZED_MESSAGE = (
    "Unauthorized.\n"
    "Open the address printed when the server started (it ends in ?token=...) "
    "on this device to sign in.\n"
)


def new_token() -> str:
    """A fresh access token (256 bits). Held in memory for one Remote mode session, never stored."""
    return secrets.token_urlsafe(32)


def is_local(request: Request) -> bool:
    client = request.client
    if client is None or client.host not in LOOPBACK_CLIENTS:
        return False
    return not any(name in request.headers for name in FORWARD_HEADERS)


def _matches(token: Optional[str], supplied: Optional[str]) -> bool:
    if not token or not supplied:
        return False
    return hmac.compare_digest(token.encode("utf-8"), supplied.encode("utf-8"))


def _is_download_link(request: Request) -> bool:
    return request.method == "GET" and _DOWNLOAD_LINK.match(request.url.path) is not None


def _bearer(request: Request) -> Optional[str]:
    scheme, _, credential = request.headers.get("authorization", "").partition(" ")
    return credential.strip() if scheme.lower() == "bearer" else None


class SecurityMiddleware:
    def __init__(self, app: ASGIApp, token: Callable[[], Optional[str]]) -> None:
        self.app = app
        # Looked up per request: the token changes each time Remote mode turns on or off.
        self._token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            # The app has no websocket endpoints; refuse rather than leave one unguarded.
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        refusal = self._check(request)
        if refusal is None:
            await self.app(scope, receive, send)
        else:
            await refusal(scope, receive, send)

    def _check(self, request: Request) -> Optional[Response]:
        token = self._token()
        if is_local(request):
            if not _LOOPBACK_HOST.match(request.headers.get("host", "")):
                return PlainTextResponse(
                    "Forbidden: this address must be opened as localhost.\n", status_code=403
                )
        elif not _matches(token, _bearer(request)) and not _is_download_link(request):
            return PlainTextResponse(UNAUTHORIZED_MESSAGE, status_code=401)

        if request.method != "GET" and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
            return PlainTextResponse(
                f"Forbidden: send the header {CSRF_HEADER}: {CSRF_VALUE}.\n", status_code=403
            )
        return None
