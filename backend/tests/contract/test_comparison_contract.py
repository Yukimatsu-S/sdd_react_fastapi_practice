"""Specify the synchronous HTTP contract for persisted Snapshot comparison."""

import inspect

from fastapi.testclient import TestClient

from app.api.routes.evolution_steps import get_evolution_step_comparison


def test_comparison_handler_is_synchronous() -> None:
    """Keep the database-backed comparison endpoint a normal function."""
    assert not inspect.iscoroutinefunction(get_evolution_step_comparison)


def test_comparison_path_exposes_documented_get_operation(client: TestClient) -> None:
    """Publish the comparison path and its successful response contract."""
    path_item = client.app.openapi()["paths"]["/api/v1/evolution-steps/{evolutionStepId}/comparison"]

    assert "get" in path_item
    assert path_item["get"]["responses"]["200"]


def test_comparison_rejects_non_positive_evolution_step_id(client: TestClient) -> None:
    """Use the shared path validation response before database access."""
    response = client.get("/api/v1/evolution-steps/0/comparison")

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
