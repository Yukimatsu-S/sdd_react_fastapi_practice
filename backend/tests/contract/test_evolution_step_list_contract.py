"""Specify the public list endpoint before its synchronous handler is added."""

import inspect

from fastapi.testclient import TestClient

from app.api.routes.evolution_steps import list_evolution_steps


def test_list_handler_is_synchronous() -> None:
    """Keep the database-backed list handler a normal function."""
    assert not inspect.iscoroutinefunction(list_evolution_steps)


def test_list_path_exposes_documented_get_operation(client: TestClient) -> None:
    """Expose a GET list operation with an opaque continuation token response."""
    path_item = client.app.openapi()["paths"]["/api/v1/evolution-steps"]

    assert "get" in path_item
    assert path_item["get"]["responses"]["200"]


def test_malformed_list_token_uses_public_validation_error(client: TestClient) -> None:
    """Reject malformed opaque tokens instead of silently treating them as a first page."""
    response = client.get("/api/v1/evolution-steps?pageToken=not-a-token")

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
