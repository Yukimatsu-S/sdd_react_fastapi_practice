"""Specify persisted current-link Lineage reads across multiple generations."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime

from app.services.lineage_service import LineageService
from sqlalchemy.engine import Connection

from app.infrastructure.evolution_step_repository import EvolutionStepRepository
from app.infrastructure.run_repository import RunReferenceRecord, RunRepository

TIME = datetime(2026, 9, 24, 10, 0, tzinfo=UTC).replace(tzinfo=None)


def _save_reference(repository: RunRepository, run_id: str, run_name: str) -> None:
    """Save one mutable Run Reference used by a Lineage edge.

    Args:
        repository: Repository sharing the test transaction.
        run_id: MLflow Run identifier used by an Evolution Step link.
        run_name: Current display name retained in the local reference.
    """
    repository.upsert_reference(
        RunReferenceRecord(
            run_id=run_id,
            mlflow_experiment_id="experiment-1",
            run_name=run_name,
            current_status="FINISHED",
            started_at=TIME,
            ended_at=TIME,
            last_synced_at=TIME,
            created_at=TIME,
        ),
    )


def test_lineage_uses_current_links_and_keeps_topology_when_run_metadata_refreshes(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
) -> None:
    """Return a selected-centered branch without treating refreshed names as links."""
    with migrated_schema() as connection:
        runs = RunRepository(connection)
        for run_id in (
            "run-external",
            "run-1",
            "run-2",
            "run-3",
            "run-4",
            "run-5",
        ):
            _save_reference(runs, run_id, f"{run_id}-before-refresh")

        steps = EvolutionStepRepository(connection)
        root = steps.create(
            purpose="Create first local Run",
            hypothesis="The external source is usable.",
            change_description=None,
            parent_run_id="run-external",
            result_run_id="run-1",
            now=TIME,
        )
        selected = steps.create(
            purpose="Improve the local baseline",
            hypothesis="A new optimizer improves accuracy.",
            change_description=None,
            parent_run_id="run-1",
            result_run_id="run-2",
            now=TIME,
        )
        first_child = steps.create(
            purpose="Branch with augmentation",
            hypothesis="Augmentation improves robustness.",
            change_description=None,
            parent_run_id="run-2",
            result_run_id="run-3",
            now=TIME,
        )
        second_child = steps.create(
            purpose="Branch with scheduling",
            hypothesis="Scheduling improves convergence.",
            change_description=None,
            parent_run_id="run-2",
            result_run_id="run-4",
            now=TIME,
        )
        grandchild = steps.create(
            purpose="Continue the augmentation branch",
            hypothesis="Longer training improves the branch.",
            change_description=None,
            parent_run_id="run-3",
            result_run_id="run-5",
            now=TIME,
        )

        service = LineageService(connection)
        before_refresh = service.get(selected.id)

        _save_reference(runs, "run-1", "run-1-after-refresh")
        after_refresh = service.get(selected.id)

        assert before_refresh.selected.evolution_step.id == selected.id
        assert before_refresh.selected.parent_evolution_step_id == root.id
        assert before_refresh.selected.distance_from_selected == 0
        assert _topology(before_refresh) == {
            "ancestors": [(root.id, None, 1)],
            "descendants": [
                (first_child.id, selected.id, 1),
                (second_child.id, selected.id, 1),
                (grandchild.id, first_child.id, 2),
            ],
        }
        assert before_refresh.selected.parent_run.run_name == "run-1-before-refresh"
        assert after_refresh.selected.parent_run.run_name == "run-1-after-refresh"
        assert _topology(after_refresh) == _topology(before_refresh)


def _topology(lineage: object) -> dict[str, list[tuple[int, int | None, int]]]:
    """Extract link-derived fields so mutable Run metadata cannot affect this assertion.

    Args:
        lineage: Selected-centered Lineage result returned by the read service.

    Returns:
        dict[str, list[tuple[int, int | None, int]]]: Stable ancestor and descendant IDs.
    """
    return {
        "ancestors": [
            (item.evolution_step.id, item.parent_evolution_step_id, item.distance_from_selected)
            for item in lineage.ancestors
        ],
        "descendants": [
            (item.evolution_step.id, item.parent_evolution_step_id, item.distance_from_selected)
            for item in lineage.descendants
        ],
    }
