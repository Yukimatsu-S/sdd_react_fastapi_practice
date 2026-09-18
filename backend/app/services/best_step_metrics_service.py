"""Read captured best-step Metrics from the local database only."""

from dataclasses import dataclass
from datetime import datetime

from app.infrastructure.run_repository import BestStepMetricRecord, RunRepository


@dataclass(frozen=True)
class BestStepMetricsResult:
    """Response-ready local best-step Metric state for one Run."""

    run_id: str
    status: str
    unavailable_reason: str | None
    best_accuracy: float | None
    best_accuracy_step: int | None
    best_accuracy_recorded_at: datetime | None
    items: tuple[BestStepMetricRecord, ...]


class BestStepMetricsService:
    """Map local Snapshot presence and accuracy data to Metric read states."""

    def __init__(self, repository: RunRepository) -> None:
        """Store the local Repository used for read-only Metric lookup.

        Args:
            repository: Run Reference and Snapshot persistence boundary.
        """
        self._repository = repository

    def get(self, run_id: str) -> BestStepMetricsResult:
        """Return locally captured Metrics without calling MLflow.

        Args:
            run_id: Locally saved Run Reference identifier.

        Returns:
            BestStepMetricsResult: Available items or an explicit unavailable state.

        Raises:
            LookupError: If the Run Reference is not stored locally.
        """
        if self._repository.get_reference(run_id) is None:
            raise LookupError(f"Run {run_id} was not found")

        snapshot = self._repository.get_snapshot(run_id)
        if snapshot is None:
            return _unavailable(run_id, "snapshot_pending")
        if snapshot.best_accuracy is None:
            return _unavailable(run_id, "accuracy_missing")
        return BestStepMetricsResult(
            run_id=run_id,
            status="available",
            unavailable_reason=None,
            best_accuracy=snapshot.best_accuracy,
            best_accuracy_step=snapshot.best_accuracy_step,
            best_accuracy_recorded_at=snapshot.best_accuracy_recorded_at,
            items=snapshot.metrics,
        )


def _unavailable(run_id: str, reason: str) -> BestStepMetricsResult:
    """Build a consistent unavailable response with no Metric items.

    Args:
        run_id: Run for which Metric data is unavailable.
        reason: Documented reason code for the unavailable state.

    Returns:
        BestStepMetricsResult: Response with null best-accuracy fields.
    """
    return BestStepMetricsResult(
        run_id=run_id,
        status="unavailable",
        unavailable_reason=reason,
        best_accuracy=None,
        best_accuracy_step=None,
        best_accuracy_recorded_at=None,
        items=(),
    )
