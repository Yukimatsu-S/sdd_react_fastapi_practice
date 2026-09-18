"""Specify persisted Evolution Step links and append-only change history."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime

import pytest
from sqlalchemy.engine import Connection, Engine

from app.infrastructure.evolution_step_repository import EvolutionStepRepository
from tests.integration.test_initial_schema import insert_reference
from tests.integration.test_initial_schema import (
    migrated_schema as _migrated_schema,
)

NOW = datetime(2026, 9, 18, 10, 0, tzinfo=UTC).replace(tzinfo=None)


@pytest.fixture(name="migrated_schema")
def migrated_schema_for_mutation_tests(
    database_engine: Engine,
) -> Callable[[], AbstractContextManager[Connection]]:
    """Reuse the migration-only context without sharing product test behavior.

    Args:
        database_engine: Dedicated test database engine from the common fixture.

    Returns:
        Callable[[], AbstractContextManager[Connection]]: Isolated migrated-schema context.
    """
    return _migrated_schema.__wrapped__(database_engine)


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
