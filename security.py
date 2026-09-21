"""Access control for everything the server serves: one ASGI middleware over every request.

A request is *local* only when it comes from a loopback address and carries no
proxy marker (a tunnel or reverse proxy on this machine also connects from
loopback). Local requests need no token but must name a loopback host, so a web
page can't reach the app by rebinding its own DNS name to 127.0.0.1. Everything
else must present the access token. State-changing requests must also carry a
custom header, which a page on another site can't add without a CORS preflight
(and no CORS header is ever sent).
"""

from __future__ import annotations

import hmac
import os
import re
import secrets
from pathlib import Path
from typing import Callable, Mapping, Optional
from urllib.parse import parse_qsl, quote, urlencode

from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

LEDGER_DIR = Path(__file__).resolve().parent / ".ledger"
TOKEN_ENV = "LEDGER_TOKEN"
COOKIE_NAME = "ledger_token"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # signed in for a year, or until the token changes

CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "ledger"

LOOPBACK_CLIENTS = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1"})
FORWARD_HEADERS = ("forwarded", "x-forwarded-for", "x-real-ip")
_LOOPBACK_HOST = re.compile(r"^(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?$", re.IGNORECASE)

UNAUTHORIZED_MESSAGE = (
    "Unauthorized.\n"
    "Open the address printed when the server started (it ends in ?token=...) "
    "on this device to sign in.\n"
)


def provision_token(directory: Path = LEDGER_DIR, environ: Mapping[str, str] = os.environ) -> str:
    """The access token: LEDGER_TOKEN if set, else the stored one, else a new one that is stored."""
    configured = environ.get(TOKEN_ENV, "").strip()
    if configured:
        return configured
    path = directory / "token"
    try:
        stored = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        stored = ""
    if stored:
        return stored
    token = secrets.token_urlsafe(32)  # 256 bits
    directory.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(token + "\n")
    return token


def is_local(request: Request) -> bool:
    client = request.client
    if client is None or client.host not in LOOPBACK_CLIENTS:
        return False
    return not any(name in request.headers for name in FORWARD_HEADERS)


def _matches(token: Optional[str], supplied: Optional[str]) -> bool:
    if not token or not supplied:
        return False
    return hmac.compare_digest(token.encode("utf-8"), supplied.encode("utf-8"))


def _bearer(request: Request) -> Optional[str]:
    scheme, _, credential = request.headers.get("authorization", "").partition(" ")
    return credential.strip() if scheme.lower() == "bearer" else None


def _without_token(request: Request) -> str:
    """The request's own path and query with every `token` parameter removed."""
    query = [
        (key, value)
        for key, value in parse_qsl(request.url.query, keep_blank_values=True)
        if key != "token"
    ]
    # Leading slashes collapse to one so the target can't read as a protocol-relative URL.
    target = quote("/" + request.url.path.lstrip("/"))
    return target + ("?" + urlencode(query) if query else "")


class SecurityMiddleware:
    def __init__(self, app: ASGIApp, token: Callable[[], Optional[str]]) -> None:
        self.app = app
        # Looked up per request: the token is only known once the CLI has parsed its options.
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
        else:
            in_query = any(_matches(token, value) for value in request.query_params.getlist("token"))
            if in_query and request.method in ("GET", "HEAD"):
                return self._sign_in(request, token)
            signed_in = (
                in_query
                or _matches(token, request.cookies.get(COOKIE_NAME))
                or _matches(token, _bearer(request))
            )
            if not signed_in:
                return PlainTextResponse(UNAUTHORIZED_MESSAGE, status_code=401)

        if request.method != "GET" and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
            return PlainTextResponse(
                f"Forbidden: send the header {CSRF_HEADER}: {CSRF_VALUE}.\n", status_code=403
            )
        return None

    @staticmethod
    def _sign_in(request: Request, token: Optional[str]) -> Response:
        """Remember this browser and drop the token from the address it lands on."""
        response = RedirectResponse(_without_token(request), status_code=303)
        # Lax, not Strict: a link opened from a QR scanner or another app is a cross-site
        # navigation, and Strict keeps the cookie off the redirect that follows it.
        response.set_cookie(
            COOKIE_NAME,
            token or "",
            max_age=COOKIE_MAX_AGE,
            path="/",
            httponly=True,
            samesite="lax",
        )
        return response
