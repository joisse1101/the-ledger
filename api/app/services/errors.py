"""Domain errors services raise; the routers' handlers turn them into HTTP responses."""

from __future__ import annotations


class ServiceError(Exception):
    """Base class; the message is what the client sees."""


class InvalidInput(ServiceError):
    """The input is well-formed but doesn't fit the stored state (HTTP 422)."""


class Conflict(ServiceError):
    """The state moved on while the caller was acting (HTTP 409)."""


class Forbidden(ServiceError):
    """The caller may not do this (HTTP 403)."""


class NotFound(ServiceError):
    """The thing asked for doesn't exist (HTTP 404)."""


class OperationFailed(ServiceError):
    """The server could not carry the request out (HTTP 500)."""


class Unavailable(ServiceError):
    """A feature the request needs isn't available right now (HTTP 503)."""
