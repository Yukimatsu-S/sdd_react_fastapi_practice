"""Specify the US1 HTTP boundary before the route modules exist."""

import inspect

from app.api.routes import evolution_steps, runs
from fastapi.testclient import TestClient


def test_us1_routes_are_synchronous_path_operations() -> None:
    """Keep database and MLflow route handlers as normal synchronous functions."""
    assert not inspect.iscoroutinefunction(evolution_steps.create_evolution_step)
    assert not inspect.iscoroutinefunction(evolution_steps.get_evolution_step)
    assert not inspect.iscoroutinefunction(evolution_steps.patch_evolution_step)
    assert not inspect.iscoroutinefunction(runs.search_runs)
    assert not inspect.iscoroutinefunction(runs.sync_run)


def test_application_registers_us1_paths(client: TestClient) -> None:
    """Expose the documented US1 paths below the versioned API prefix."""
    operations = {
        (route.path, method)
        for route in client.app.routes
        for method in getattr(route, "methods", set())
    }

    assert ("/api/v1/evolution-steps", "POST") in operations
    assert ("/api/v1/evolution-steps/{evolutionStepId}", "GET") in operations
    assert ("/api/v1/evolution-steps/{evolutionStepId}", "PATCH") in operations
    assert ("/api/v1/runs", "GET") in operations
    assert ("/api/v1/runs/{runId}/sync", "POST") in operations


def test_invalid_us1_path_values_return_the_public_validation_envelope(
    client: TestClient,
) -> None:
    """Reject malformed IDs with the common documented error fields."""
    response = client.get("/api/v1/evolution-steps/0")

    assert response.status_code == 422
    assert response.json() == {
        "code": "validation_error",
        "message": "Request validation failed.",
        "traceId": response.json()["traceId"],
    }
