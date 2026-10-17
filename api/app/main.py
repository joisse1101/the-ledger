"""The FastAPI app: middleware, startup/shutdown and the routers."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from app import deps, refresh
from app.core.config import parse_settings
from app.core.security import SecurityMiddleware, provision_token
from app.routers import decisions, files, live, meta, overview, projects, remote_mode, sessions, transcripts

log = logging.getLogger("ledger")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Normally already set by main() before this process's own uvicorn.run() call, so this is a
    # no-op then. --reload's subprocess is the exception: uvicorn imports "app.main:app" fresh in a
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
