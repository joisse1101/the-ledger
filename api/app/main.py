"""The FastAPI app: middleware, startup/shutdown and the routers."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from app import deps, refresh
from app.core.config import parse_settings
from app.core.security import SecurityMiddleware
from app.routers.errors import register_error_handlers
from app.routers import auto_approve, decisions, files, live, meta, overview, projects, remote_mode, sessions, settings, transcripts

log = logging.getLogger("ledger")


@asynccontextmanager
async def lifespan(app: FastAPI):
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

register_error_handlers(app)
for module in (meta, remote_mode, live, transcripts, sessions, decisions, auto_approve, files, projects, overview, settings):
    app.include_router(module.router)
