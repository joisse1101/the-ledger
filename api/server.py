"""FastAPI server for the dashboard: a JSON API over the claude_* data modules."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, Sequence

import uvicorn
from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from app import deps, refresh
from app.core.config import parse_settings
from app.core.security import SecurityMiddleware, provision_token
from app.infra import banner
from app.routers import decisions, files, live, meta, overview, projects, remote_mode, sessions, transcripts

log = logging.getLogger("ledger")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Normally already set by main() before this process's own uvicorn.run() call, so this is a
    # no-op then. --reload's subprocess is the exception: uvicorn imports "server:app" fresh in a
    # separate process that never runs main() at all, so this is that process's only chance to
    # provision the token it actually serves with (re-reads the same stored file main() already
    # wrote, so it's the same token either way).
    if deps.access_token is None:
        deps.access_token = provision_token()

    if deps.remote is None:
        env_settings = parse_settings([])
        deps.remote = deps.make_remote(env_settings.port, env_settings.frontend_port)
    # Remote mode starts off, so a gateway an earlier backend left running is closed now.
    await asyncio.to_thread(deps.remote.stop_leftovers)

    await asyncio.to_thread(refresh.startup_snapshot)
    task = asyncio.create_task(refresh.refresh_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="The Ledger",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(SecurityMiddleware, token=lambda: deps.access_token)

for module in (meta, remote_mode, live, transcripts, sessions, decisions, files, projects, overview):
    app.include_router(module.router)


def main(argv: Optional[Sequence[str]] = None) -> None:
    settings = parse_settings(argv)

    # Provisioned unconditionally: the gateway (a separate process) is what decides whether
    # anyone off this machine can ever present it, so the backend no longer gates this on
    # its own bind address.
    deps.access_token = provision_token()
    deps.remote = deps.make_remote(settings.port, settings.frontend_port)

    print(banner.build_banner(frontend_port=settings.frontend_port), flush=True)

    # No access log: it would write every ?token=... URL to the terminal. proxy_headers off:
    # the peer address must stay the real one, not whatever a header claims.
    if settings.reload:
        # The reload subprocess builds its own Remote mode lifecycle (see lifespan()); the ports
        # reach it through the same env vars parse_settings reads.
        os.environ["LEDGER_PORT"] = str(settings.port)
        os.environ["LEDGER_FRONTEND_PORT"] = str(settings.frontend_port)
        # reload=True only takes effect when the app is passed as an import string - uvicorn
        # watches the cwd, and on each change spawns a fresh subprocess that imports "server:app"
        # itself (this process's own `app` object above is never reused); see lifespan() for how
        # that subprocess still gets a token.
        uvicorn.run(
            "server:app",
            host=settings.host,
            port=settings.port,
            reload=True,
            access_log=False,
            proxy_headers=False,
        )
    else:
        uvicorn.run(app, host=settings.host, port=settings.port, access_log=False, proxy_headers=False)


if __name__ == "__main__":
    main()
