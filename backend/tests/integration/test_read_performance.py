"""Measure local read budgets against a fixed, migration-created MySQL dataset."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy.engine import Connection

from app.infrastructure.evolution_step_repository import EvolutionStepRepository
from app.infrastructure.run_repository import RunReferenceRecord, RunRepository
from app.services.comparison_service import ComparisonService
from app.services.evolution_step_list_service import EvolutionStepListService
from app.services.lineage_service import LineageService

TIME = datetime(2026, 9, 24, 10, 0, tzinfo=UTC).replace(tzinfo=None)
MEASURED_RUNS = 30
WARM_UP_RUNS = 5


def test_local_read_budgets_with_one_thousand_steps_and_a_hundred_step_lineage(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
) -> None:
    """Keep local list, detail, comparison, and Lineage reads within their budgets."""
    with migrated_schema() as connection:
        selected_id = _seed_steps(connection)
        reads = {
            "list": lambda: EvolutionStepListService(connection).list(None),
            "detail": lambda: EvolutionStepRepository(connection).get(selected_id),
            "comparison": lambda: ComparisonService(connection).get(selected_id),
            "lineage": lambda: LineageService(connection).get(selected_id),
        }

        results = {name: _p95_seconds(read) for name, read in reads.items()}

    assert results["list"] <= 0.5
    assert results["detail"] <= 0.5
    assert results["comparison"] <= 0.5
    assert results["lineage"] <= 1.0


def _seed_steps(connection: Connection) -> int:
    """Create 1,000 current Steps whose first 100 form one connected Lineage.

    Args:
        connection: Migration-created MySQL connection used only by this test.

    Returns:
        int: Middle Step ID in the connected 100-Step Lineage.
    """
    runs = RunRepository(connection)
    for number in range(101):
        run_id = f"performance-run-{number:04d}"
        runs.upsert_reference(
            RunReferenceRecord(
                run_id=run_id,
                mlflow_experiment_id="performance-experiment",
                run_name=run_id,
                current_status="FINISHED",
                started_at=TIME,
                ended_at=TIME,
                last_synced_at=TIME,
                created_at=TIME,
            ),
        )

    steps = EvolutionStepRepository(connection)
    for number in range(1000):
        parent_run_id = (
            f"performance-run-{number:04d}"
            if number < 100
            else None
        )
        result_run_id = (
            f"performance-run-{number + 1:04d}"
            if number < 100
            else None
        )
        steps.create(
            purpose=f"Performance Step {number}",
            hypothesis="Read performance remains within the local budget.",
            change_description=None,
            parent_run_id=parent_run_id,
            result_run_id=result_run_id,
            now=TIME,
        )
    connection.commit()
    return 50


def _p95_seconds(read: Callable[[], object]) -> float:
    """Measure nearest-rank p95 after unmeasured warm-up reads.

    Args:
        read: Local read operation whose fixture setup and synchronization are excluded.

    Returns:
        float: Nearest-rank 95th percentile duration in seconds.
    """
    for _ in range(WARM_UP_RUNS):
        read()

    durations: list[float] = []
    for _ in range(MEASURED_RUNS):
        started_at = perf_counter()
        read()
        durations.append(perf_counter() - started_at)

    ordered = sorted(durations)
    rank = max(1, round(MEASURED_RUNS * 0.95))
    return ordered[rank - 1]
