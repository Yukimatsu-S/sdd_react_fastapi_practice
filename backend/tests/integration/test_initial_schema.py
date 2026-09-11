"""T012: inspect model definitions without creating database tables.

Migration-backed checks will be added separately. These checks deliberately use
empty importable metadata until T013 supplies the actual table definitions.
"""

import pytest
from sqlalchemy import UniqueConstraint

from app.infrastructure.models import metadata

EXPECTED_COLUMNS = {
    "evolution_step": {
        "id", "purpose", "hypothesis", "change_description", "parent_run_id",
        "result_run_id", "created_at", "updated_at",
    },
    "lineage_mutation_guard": {"id"},
    "run_reference": {
        "run_id", "mlflow_experiment_id", "run_name", "current_status",
        "started_at", "ended_at", "last_synced_at", "created_at",
    },
    "run_snapshot": {
        "run_id", "status_at_capture", "started_at", "ended_at", "best_accuracy",
        "best_accuracy_step", "best_accuracy_recorded_at", "captured_at",
        "raw_metadata",
    },
    "run_parameter": {"run_id", "name", "value"},
    "best_step_metric": {"run_id", "name", "value", "step", "recorded_at"},
    "dataset_input": {
        "id", "run_id", "ordinal", "name", "digest", "source_type", "source",
        "schema", "profile", "context", "raw_metadata",
    },
    "evolution_step_history": {
        "id", "evolution_step_id", "field", "old_value", "new_value", "changed_at",
    },
}

EXPECTED_PRIMARY_KEYS = [
    ("evolution_step", ("id",)),
    ("lineage_mutation_guard", ("id",)),
    ("run_reference", ("run_id",)),
    ("run_snapshot", ("run_id",)),
    ("run_parameter", ("run_id", "name")),
    ("best_step_metric", ("run_id", "name")),
    ("dataset_input", ("id",)),
    ("evolution_step_history", ("id",)),
]


def require_table(name):
    """Fail at a schema assertion rather than a missing-table KeyError."""
    assert name in metadata.tables, f"Model metadata must define table: {name}"
    return metadata.tables[name]


def test_model_metadata_contains_all_product_tables():
    assert set(metadata.tables) == set(EXPECTED_COLUMNS)


@pytest.mark.parametrize("table_name", EXPECTED_COLUMNS)
def test_model_metadata_columns(table_name):
    table = require_table(table_name)
    assert set(table.c.keys()) == EXPECTED_COLUMNS[table_name]


@pytest.mark.parametrize("table_name, columns", EXPECTED_PRIMARY_KEYS)
def test_model_metadata_primary_keys(table_name, columns):
    table = require_table(table_name)
    assert tuple(table.primary_key.columns.keys()) == columns


@pytest.mark.parametrize("table_name, column_name, target", [
    ("evolution_step", "parent_run_id", "run_reference.run_id"),
    ("evolution_step", "result_run_id", "run_reference.run_id"),
    ("run_snapshot", "run_id", "run_reference.run_id"),
    ("run_parameter", "run_id", "run_snapshot.run_id"),
    ("best_step_metric", "run_id", "run_snapshot.run_id"),
    ("dataset_input", "run_id", "run_snapshot.run_id"),
    ("evolution_step_history", "evolution_step_id", "evolution_step.id"),
])
def test_model_metadata_foreign_keys(table_name, column_name, target):
    table = require_table(table_name)
    assert {key.target_fullname for key in table.c[column_name].foreign_keys} == {target}


@pytest.mark.parametrize("table_name, columns", [
    ("evolution_step", ("result_run_id",)),
    ("dataset_input", ("run_id", "ordinal")),
])
def test_model_metadata_unique_keys(table_name, columns):
    table = require_table(table_name)
    unique_keys = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    unique_keys.update(
        tuple(index.columns.keys()) for index in table.indexes if index.unique
    )
    assert columns in unique_keys


@pytest.mark.parametrize("column_name, nullable", [
    ("purpose", False),
    ("hypothesis", False),
    ("change_description", True),
    ("parent_run_id", True),
    ("result_run_id", True),
])
def test_model_metadata_step_nullability(column_name, nullable):
    table = require_table("evolution_step")
    assert table.c[column_name].nullable is nullable


def test_model_metadata_parent_run_is_not_unique():
    table = require_table("evolution_step")
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            assert tuple(constraint.columns.keys()) != ("parent_run_id",)
    for index in table.indexes:
        if index.unique:
            assert tuple(index.columns.keys()) != ("parent_run_id",)
