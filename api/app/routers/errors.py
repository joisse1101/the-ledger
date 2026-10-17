"""Map the services' domain errors to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.errors import Conflict, Forbidden, InvalidInput, NotFound, ServiceError

STATUS_BY_ERROR: dict[type[ServiceError], int] = {
    InvalidInput: 422,
    Conflict: 409,
    Forbidden: 403,
    NotFound: 404,
}


def register_error_handlers(app: FastAPI) -> None:
    for error_type, status_code in STATUS_BY_ERROR.items():
        def handler(request: Request, exc: ServiceError, status_code: int = status_code) -> JSONResponse:
            return JSONResponse({"detail": str(exc)}, status_code=status_code)

        app.add_exception_handler(error_type, handler)
