"""Local read service for a full immutable-Snapshot comparison."""

from typing import Any

from sqlalchemy.engine import Connection

from app.domain.comparison import Comparison, build_comparison
from app.infrastructure.evolution_step_repository import EvolutionStepRepository
from app.infrastructure.run_repository import RunRepository, RunSnapshotRecord


class ComparisonService:
    """Read one Evolution Step and compare only its captured Snapshot data."""

    def __init__(self, connection: Connection) -> None:
        """Create repositories sharing one caller-owned database connection.

        Args:
            connection: Connection used only for local Snapshot reads.
        """
        self._steps = EvolutionStepRepository(connection)
        self._runs = RunRepository(connection)

    def get(self, evolution_step_id: int) -> Comparison:
        """Build one comparison for the Step's current parent and result links.

        Args:
            evolution_step_id: Positive local Evolution Step identifier.

        Returns:
            Comparison: Immutable Snapshot differences or explicit unavailable state.

        Raises:
            LookupError: If the requested Evolution Step does not exist.
        """
        step = self._steps.get(evolution_step_id)
        return assemble_comparison(
            parent_run_id=step.parent_run_id,
            parent_snapshot=_snapshot_values(self._runs.get_snapshot(step.parent_run_id)),
            result_run_id=step.result_run_id,
            result_snapshot=_snapshot_values(self._runs.get_snapshot(step.result_run_id)),
        )


def assemble_comparison(
    parent_run_id: str | None,
    parent_snapshot: dict[str, Any] | None,
    result_run_id: str | None,
    result_snapshot: dict[str, Any] | None,
) -> Comparison:
    """Expose pure comparison assembly for unit tests and local read services.

    Args:
        parent_run_id: Current parent Run link, if selected.
        parent_snapshot: Immutable parent Snapshot values, if captured.
        result_run_id: Current result Run link, if selected.
        result_snapshot: Immutable result Snapshot values, if captured.

    Returns:
        Comparison: Full comparison calculated from immutable values only.
    """
    return build_comparison(parent_run_id, parent_snapshot, result_run_id, result_snapshot)


def _snapshot_values(snapshot: RunSnapshotRecord | None) -> dict[str, Any] | None:
    """Extract only immutable fields used by comparison calculations.

    Args:
        snapshot: Captured local Snapshot, if available.

    Returns:
        dict[str, Any] | None: Comparison values, or ``None`` when pending.
    """
    if snapshot is None:
        return None
    return {
        "parameters": snapshot.parameters,
        "best_accuracy": snapshot.best_accuracy,
        "datasets": snapshot.datasets,
    }
