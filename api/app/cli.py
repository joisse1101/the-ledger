"""`python -m app`: parse the settings and serve the app with uvicorn."""

from __future__ import annotations

import os
from typing import Optional, Sequence

import uvicorn

from app import deps
from app.core.config import parse_settings
from app.infra import banner
from app.main import app


def main(argv: Optional[Sequence[str]] = None) -> None:
    settings = parse_settings(argv)

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
        # watches the cwd, and on each change spawns a fresh subprocess that imports "app.main:app"
        # itself (this process's own `app` object above is never reused).
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=True,
            access_log=False,
            proxy_headers=False,
        )
    else:
        uvicorn.run(app, host=settings.host, port=settings.port, access_log=False, proxy_headers=False)
