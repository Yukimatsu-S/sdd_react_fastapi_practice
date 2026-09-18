"""Specify the local best-step Metric HTTP response contract."""

import inspect

from app.api.routes import runs
from app.api.schemas.runs import BestStepMetricsResponse


def test_schema_keeps_available_metric_items_and_signed_steps() -> None:
    """Serialize the captured Metrics at the selected signed best step."""
    response = BestStepMetricsResponse(
        run_id="run-finished",
        status="available",
        unavailable_reason=None,
        best_accuracy=0.91,
        best_accuracy_step=-1,
        best_accuracy_recorded_at="2026-09-18T11:00:00Z",
        items=[
            {
                "name": "accuracy",
                "value": 0.91,
                "step": -1,
                "recorded_at": "2026-09-18T11:00:00Z",
            },
        ],
    )

    assert response.model_dump(by_alias=True)["bestAccuracyStep"] == -1


def test_best_step_metric_route_is_synchronous() -> None:
    """Keep the database-backed best-step read as a normal path operation."""
    assert not inspect.iscoroutinefunction(runs.get_best_step_metrics)
