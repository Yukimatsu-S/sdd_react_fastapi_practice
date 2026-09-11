"""T012: inspect model definitions without creating database tables.

Migration-backed checks will be added separately. These checks deliberately use
empty importable metadata until T013 supplies the actual table definitions.
"""

import pytest
from sqlalchemy import Enum, UniqueConstraint
from sqlalchemy.dialects import mysql

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


EXPECTED_HISTORY_FIELDS = {
    "purpose",
    "hypothesis",
    "change_description",
    "parent_run_id",
    "result_run_id",
}


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
    # Reject missing keys and extra uniqueness rules that restrict valid data.
    assert unique_keys == {columns}


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


@pytest.mark.parametrize("table_name, column_name", [
    ("evolution_step", "id"),
    ("run_snapshot", "best_accuracy_step"),
    ("best_step_metric", "step"),
    ("evolution_step_history", "id"),
    ("evolution_step_history", "evolution_step_id"),
])
def test_model_metadata_signed_bigint(table_name, column_name):
    table = require_table(table_name)
    column_type = table.c[column_name].type
    # Check the MySQL type, not the Python class chosen to express it.
    mysql_type = column_type.compile(dialect=mysql.dialect())
    assert mysql_type == "BIGINT"


@pytest.mark.parametrize("table_name, column_name", [
    ("evolution_step", "created_at"),
    ("evolution_step", "updated_at"),
    ("run_reference", "started_at"),
    ("run_reference", "ended_at"),
    ("run_reference", "last_synced_at"),
    ("run_reference", "created_at"),
    ("run_snapshot", "started_at"),
    ("run_snapshot", "ended_at"),
    ("run_snapshot", "best_accuracy_recorded_at"),
    ("run_snapshot", "captured_at"),
    ("best_step_metric", "recorded_at"),
    ("evolution_step_history", "changed_at"),
])
def test_model_metadata_datetime_precision(table_name, column_name):
    table = require_table(table_name)
    column_type = table.c[column_name].type
    mysql_type = column_type.compile(dialect=mysql.dialect())
    assert mysql_type == "DATETIME(6)"


@pytest.mark.parametrize("expected_expressions", [
    ("parent_run_id",),
    ("created_at DESC", "id DESC"),
])
def test_model_metadata_search_indexes(expected_expressions):
    table = require_table("evolution_step")
    non_unique_indexes = set()
    for index in table.indexes:
        if not index.unique:
            expressions = tuple(
                str(expression.compile(
                    dialect=mysql.dialect(),
                    compile_kwargs={"include_table": False},
                ))
                for expression in index.expressions
            )
            non_unique_indexes.add(expressions)
    # Names are implementation details; column order and DESC are the contract.
    assert expected_expressions in non_unique_indexes


@pytest.mark.parametrize("table_name, column_name, expected_type", [
    ("evolution_step", "purpose", "TEXT"),
    ("evolution_step", "hypothesis", "TEXT"),
    ("evolution_step", "change_description", "TEXT"),
    ("evolution_step", "parent_run_id", "VARCHAR(64)"),
    ("evolution_step", "result_run_id", "VARCHAR(64)"),
    ("lineage_mutation_guard", "id", "TINYINT"),
    ("run_reference", "run_id", "VARCHAR(64)"),
    ("run_reference", "mlflow_experiment_id", "VARCHAR(64)"),
    ("run_reference", "run_name", "VARCHAR(255)"),
    ("run_reference", "current_status", "VARCHAR(16)"),
    ("run_snapshot", "run_id", "VARCHAR(64)"),
    ("run_snapshot", "status_at_capture", "VARCHAR(16)"),
    ("run_snapshot", "best_accuracy", "DOUBLE"),
    ("run_snapshot", "raw_metadata", "JSON"),
    ("best_step_metric", "value", "DOUBLE"),
    ("dataset_input", "ordinal", "INTEGER"),
    ("dataset_input", "raw_metadata", "JSON"),
    ("evolution_step_history", "old_value", "TEXT"),
    ("evolution_step_history", "new_value", "TEXT"),
])
def test_model_metadata_other_declared_types(table_name, column_name, expected_type):
    table = require_table(table_name)
    mysql_type = table.c[column_name].type.compile(dialect=mysql.dialect())
    assert mysql_type == expected_type


@pytest.mark.parametrize("table_name, column_name, nullable", [
    ("evolution_step", "created_at", False),
    ("evolution_step", "updated_at", False),
    ("run_reference", "mlflow_experiment_id", True),
    ("run_reference", "run_name", True),
    ("run_reference", "current_status", False),
    ("run_reference", "started_at", True),
    ("run_reference", "ended_at", True),
    ("run_reference", "last_synced_at", False),
    ("run_reference", "created_at", False),
    ("run_snapshot", "status_at_capture", False),
    ("run_snapshot", "started_at", True),
    ("run_snapshot", "ended_at", True),
    ("run_snapshot", "best_accuracy", True),
    ("run_snapshot", "best_accuracy_step", True),
    ("run_snapshot", "best_accuracy_recorded_at", True),
    ("run_snapshot", "captured_at", False),
    ("run_snapshot", "raw_metadata", True),
    ("dataset_input", "schema", True),
    ("dataset_input", "profile", True),
    ("dataset_input", "context", True),
    ("dataset_input", "raw_metadata", True),
    ("evolution_step_history", "evolution_step_id", False),
    ("evolution_step_history", "field", False),
    ("evolution_step_history", "old_value", True),
    ("evolution_step_history", "new_value", True),
    ("evolution_step_history", "changed_at", False),
])
def test_model_metadata_other_declared_nullability(table_name, column_name, nullable):
    table = require_table(table_name)
    assert table.c[column_name].nullable is nullable


def test_model_metadata_history_field_enum():
    table = require_table("evolution_step_history")
    field_type = table.c.field.type
    assert isinstance(field_type, Enum)
    assert field_type.native_enum is True
    assert set(field_type.enums) == EXPECTED_HISTORY_FIELDS
