"""Domain errors reach the client as the HTTP status and body the routes always returned."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.errors import register_error_handlers
from app.services.errors import Conflict, Forbidden, InvalidInput, NotFound


@pytest.mark.parametrize(
    ("error", "status"),
    [(InvalidInput, 422), (Conflict, 409), (Forbidden, 403), (NotFound, 404)],
)
def test_error_maps_to_status_and_detail(error, status):
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise error("nope")

    response = TestClient(app).get("/boom")
    assert (response.status_code, response.json()) == (status, {"detail": "nope"})
