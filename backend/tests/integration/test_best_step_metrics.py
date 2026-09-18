"""Specify local best-step Metric reads without an MLflow request."""

from app.services.best_step_metrics_service import BestStepMetricsService


def test_pending_reference_returns_snapshot_pending() -> None:
    """Return an explicit unavailable state before a Snapshot exists."""
    service = BestStepMetricsService(repository=object())

    response = service.get("run-pending")

    assert response.status == "unavailable"
    assert response.unavailable_reason == "snapshot_pending"
    assert response.items == ()
