"""Specify persisted Evolution Step links and append-only change history."""

from datetime import UTC, datetime

import pytest

from app.domain.lineage import ResultRunConflictError
from app.infrastructure.evolution_step_repository import EvolutionStepRepository
from app.infrastructure.mlflow_gateway import LoadedRun
from app.services.evolution_step_service import EvolutionStepService
from tests.integration.test_initial_schema import insert_reference

NOW = datetime(2026, 9, 18, 10, 0, tzinfo=UTC).replace(tzinfo=None)


class StaticRunLoader:
    """Return selected Run metadata without contacting MLflow in this test."""

    def __init__(self, runs: dict[str, LoadedRun]) -> None:
        """Store deterministic loaded Runs by their identifiers.

        Args:
            runs: MLflow-shaped Runs returned to the create service.
        """
        self._runs = runs

    def load(self, run_id: str) -> LoadedRun:
        """Return the configured selected Run.

        Args:
            run_id: Run identifier selected by the create request.

        Returns:
            LoadedRun: Current metadata configured for this test.
        """
        return self._runs[run_id]


def test_repository_allows_shared_parent_and_records_only_actual_changes(migrated_schema) -> None:
    """Keep shared parent links while omitting no-op updates from history."""
    with migrated_schema() as connection:
        for run_id in ("run-parent", "run-result-a", "run-result-b"):
            insert_reference(connection, run_id)
        repository = EvolutionStepRepository(connection)
        first = repository.create(
            purpose="Improve baseline",
            hypothesis="Augmentation improves accuracy.",
            change_description="Try augmentation.",
            parent_run_id="run-parent",
            result_run_id="run-result-a",
            now=NOW,
        )
        second = repository.create(
            purpose="Try a different optimizer",
            hypothesis="Optimizer choice improves convergence.",
            change_description=None,
            parent_run_id="run-parent",
            result_run_id="run-result-b",
            now=NOW,
        )

        unchanged = repository.update(first.id, {"purpose": "Improve baseline"}, NOW)
        updated = repository.update(
            first.id,
            {"change_description": None, "parent_run_id": None},
            NOW,
        )

        history = repository.history(first.id)
        assert second.parent_run_id == "run-parent"
        assert unchanged == first
        assert updated.change_description is None
        assert updated.parent_run_id is None
        assert [(item.field, item.old_value, item.new_value) for item in history] == [
            ("change_description", "Try augmentation.", None),
            ("parent_run_id", "run-parent", None),
        ]


def test_repository_orders_same_timestamp_history_by_internal_id(migrated_schema) -> None:
    """Return a deterministic order when one update changes multiple fields."""
    with migrated_schema() as connection:
        insert_reference(connection, "run-result")
        repository = EvolutionStepRepository(connection)
        step = repository.create(
            purpose="Initial purpose",
            hypothesis="Initial hypothesis",
            change_description=None,
            parent_run_id=None,
            result_run_id="run-result",
            now=NOW,
        )

        repository.update(
            step.id,
            {"purpose": "Updated purpose", "hypothesis": "Updated hypothesis"},
            NOW,
        )

        assert [item.field for item in repository.history(step.id)] == ["purpose", "hypothesis"]


def test_create_service_persists_selected_references_without_initial_history(migrated_schema) -> None:
    """Create a Step after selected Runs are read and saved as references."""
    parent = LoadedRun("run-parent", "experiment-1", "parent", "FINISHED", NOW, NOW, None)
    result = LoadedRun("run-result", "experiment-1", "result", "RUNNING", NOW, None, None)
    with migrated_schema() as connection:
        service = EvolutionStepService(connection, StaticRunLoader({
            "run-parent": parent,
            "run-result": result,
        }))

        created = service.create(
            purpose="Improve baseline",
            hypothesis="Augmentation improves accuracy.",
            change_description=None,
            parent_run_id="run-parent",
            result_run_id="run-result",
            now=NOW,
        )

        repository = EvolutionStepRepository(connection)
        assert created.parent_run_id == "run-parent"
        assert created.result_run_id == "run-result"
        assert repository.history(created.id) == ()


def test_create_service_rejects_an_already_claimed_result_run(migrated_schema) -> None:
    """Roll back a create request that attempts to reuse a result Run."""
    selected = LoadedRun("run-result", "experiment-1", "result", "FINISHED", NOW, NOW, None)
    with migrated_schema() as connection:
        insert_reference(connection, "run-result")
        existing = EvolutionStepRepository(connection).create(
            purpose="Existing",
            hypothesis="Existing hypothesis.",
            change_description=None,
            parent_run_id=None,
            result_run_id="run-result",
            now=NOW,
        )
        connection.commit()
        service = EvolutionStepService(connection, StaticRunLoader({"run-result": selected}))

        with pytest.raises(ResultRunConflictError):
            service.create(
                purpose="Another",
                hypothesis="Another hypothesis.",
                change_description=None,
                parent_run_id=None,
                result_run_id="run-result",
                now=NOW,
            )

        assert EvolutionStepRepository(connection).get(existing.id) == existing


def test_patch_service_updates_text_and_explicitly_unlinks_runs(migrated_schema) -> None:
    """Apply only actual changes and retain each previous value in history."""
    parent = LoadedRun("run-parent", "experiment-1", "parent", "FINISHED", NOW, NOW, None)
    result = LoadedRun("run-result", "experiment-1", "result", "RUNNING", NOW, None, None)
    with migrated_schema() as connection:
        service = EvolutionStepService(connection, StaticRunLoader({
            "run-parent": parent,
            "run-result": result,
        }))
        created = service.create(
            purpose="Improve baseline",
            hypothesis="Augmentation improves accuracy.",
            change_description="Use a crop.",
            parent_run_id="run-parent",
            result_run_id="run-result",
            now=NOW,
        )

        updated = service.patch(
            created.id,
            {"purpose": "Improve baseline v2", "parent_run_id": None},
            NOW,
        )

        assert updated.purpose == "Improve baseline v2"
        assert updated.parent_run_id is None
        assert [item.field for item in EvolutionStepRepository(connection).history(created.id)] == [
            "purpose",
            "parent_run_id",
        ]
