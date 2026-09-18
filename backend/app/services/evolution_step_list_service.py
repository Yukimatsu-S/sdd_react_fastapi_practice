"""Local-only orchestration for token-paginated Evolution Step list responses."""

from dataclasses import dataclass

from sqlalchemy.engine import Connection

from app.domain.comparison import ComparisonSummary, build_comparison_summary
from app.infrastructure.evolution_step_repository import (
    EvolutionStepRecord,
    EvolutionStepRepository,
)
from app.infrastructure.run_repository import RunRepository, RunSnapshotRecord


@dataclass(frozen=True)
class EvolutionStepListItem:
    """Current Step fields together with its compact immutable comparison summary."""

    step: EvolutionStepRecord
    comparison_summary: ComparisonSummary


@dataclass(frozen=True)
class EvolutionStepListResult:
    """One list response payload before HTTP serialization."""

    items: tuple[EvolutionStepListItem, ...]
    next_page_token: str | None


class EvolutionStepListService:
    """Read current Steps and summarize local captured Snapshot differences."""

    def __init__(self, connection: Connection) -> None:
        """Create repositories sharing the caller-owned database connection.

        Args:
            connection: Connection used only for local MySQL reads.
        """
        self._steps = EvolutionStepRepository(connection)
        self._runs = RunRepository(connection)

    def list(self, page_token: str | None) -> EvolutionStepListResult:
        """Map one deterministic repository page to local list summary items.

        Args:
            page_token: Optional opaque continuation token.

        Returns:
            Current Steps and summary fields without synchronizing MLflow.
        """
        page = self._steps.list_page(page_token)
        return EvolutionStepListResult(
            items=tuple(
                EvolutionStepListItem(
                    step=step,
                    comparison_summary=build_comparison_summary(
                        _snapshot_values(self._runs.get_snapshot(step.parent_run_id)),
                        _snapshot_values(self._runs.get_snapshot(step.result_run_id)),
                    ),
                )
                for step in page.items
            ),
            next_page_token=page.next_page_token,
        )


def _snapshot_values(snapshot: RunSnapshotRecord | None) -> dict[str, object] | None:
    """Extract only immutable fields used by compact comparison calculation.

    Args:
        snapshot: Locally captured terminal Snapshot, if available.

    Returns:
        Values accepted by the comparison domain helper, or ``None`` when pending.
    """
    if snapshot is None:
        return None
    return {
        "parameters": snapshot.parameters,
        "best_accuracy": snapshot.best_accuracy,
        "datasets": snapshot.datasets,
    }
