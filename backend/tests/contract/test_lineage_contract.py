"""Specify the public synchronous Lineage endpoint and response fields."""

import inspect

from fastapi.testclient import TestClient

from app.api.routes.evolution_steps import get_evolution_step_lineage
from app.api.schemas.lineage import LineageResponse, LineageStepResponse


def test_lineage_handler_is_synchronous() -> None:
    """Keep the database-backed Lineage handler a normal function."""
    assert not inspect.iscoroutinefunction(get_evolution_step_lineage)


def test_lineage_path_exposes_documented_get_operation(client: TestClient) -> None:
    """Expose a GET operation for one selected-centered Lineage."""
    path_item = client.app.openapi()["paths"]["/api/v1/evolution-steps/{evolutionStepId}/lineage"]

    assert "get" in path_item
    assert path_item["get"]["responses"]["200"]
    assert path_item["get"]["responses"]["404"]
    assert path_item["get"]["responses"]["422"]


def test_lineage_schema_keeps_distances_parent_step_and_external_boundary() -> None:
    """Serialize a selected Step and an external parent Run boundary explicitly."""
    response = LineageResponse(
        selected=LineageStepResponse(
            id=2,
            purpose="Improve the baseline",
            hypothesis="A new optimizer improves accuracy.",
            parent_evolution_step_id=1,
            distance_from_selected=0,
            parent_run={
                "run_id": "run-1",
                "mlflow_experiment_id": "experiment-1",
                "run_name": "baseline",
                "current_status": "FINISHED",
                "started_at": "2026-09-24T10:00:00Z",
                "ended_at": "2026-09-24T10:10:00Z",
                "last_synced_at": "2026-09-24T10:10:00Z",
                "snapshot_state": "captured",
                "snapshot_captured_at": "2026-09-24T10:10:00Z",
            },
            result_run=None,
        ),
        ancestors=[
            LineageStepResponse(
                id=1,
                purpose="Create a local baseline",
                hypothesis="The external source is usable.",
                parent_evolution_step_id=None,
                distance_from_selected=1,
                parent_run={
                    "run_id": "run-external",
                    "mlflow_experiment_id": None,
                    "run_name": None,
                    "current_status": "FINISHED",
                    "started_at": None,
                    "ended_at": None,
                    "last_synced_at": "2026-09-24T10:00:00Z",
                    "snapshot_state": "pending",
                    "snapshot_captured_at": None,
                },
                result_run=None,
            ),
        ],
        descendants=[],
    )

    body = response.model_dump(by_alias=True)

    assert body["selected"]["distanceFromSelected"] == 0
    assert body["selected"]["parentEvolutionStepId"] == 1
    assert body["ancestors"][0]["distanceFromSelected"] == 1
    assert body["ancestors"][0]["parentEvolutionStepId"] is None
    assert body["ancestors"][0]["parentRun"]["runId"] == "run-external"
