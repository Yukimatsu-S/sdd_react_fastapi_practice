"""Specify local best-step Metric reads without an MLflow request."""

from app.services.best_step_metrics_service import BestStepMetricsService


class PendingRepository:
    """Expose a saved Reference without a captured Snapshot."""

    def get_reference(self, run_id: str) -> object:
        """Return a sentinel proving the Run is known locally.

        Args:
            run_id: Requested Run identifier.

        Returns:
            object: Local Reference sentinel.
        """
        return object()

    def get_snapshot(self, run_id: str) -> None:
        """Return no Snapshot while the Run remains pending.

        Args:
            run_id: Requested Run identifier.

        Returns:
            None: Pending Runs have no Snapshot payload.
        """
        return


def test_pending_reference_returns_snapshot_pending() -> None:
    """Return an explicit unavailable state before a Snapshot exists."""
    service = BestStepMetricsService(repository=PendingRepository())

    response = service.get("run-pending")

    assert response.status == "unavailable"
    assert response.unavailable_reason == "snapshot_pending"
    assert response.items == ()
