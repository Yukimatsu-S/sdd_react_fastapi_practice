"""T012: verify independent model definitions and actual migration-created tables."""

import importlib.util
import sys
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Enum, MetaData, Table, UniqueConstraint, inspect, text
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

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

INITIAL_MIGRATION = (
    Path(__file__).resolve().parents[2] / "migrations/versions/001_initial_schema.py"
)
SCHEMA_DROP_ORDER = (
    "evolution_step_history", "dataset_input", "best_step_metric", "run_parameter",
    "run_snapshot", "evolution_step", "run_reference", "lineage_mutation_guard",
    "alembic_version",
)
RECOVERY_HINT = (
    "Existing migration targets must be preserved. Follow section 10 of "
    "docs/learning/database-sessions-and-transactions.md; do not delete them automatically."
)
SAMPLE_TIME = datetime(2026, 9, 15, 10, 20, 30, 123456, tzinfo=UTC).replace(tzinfo=None)


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


@pytest.fixture
def migrated_schema(database_engine: Engine) -> Callable[[], AbstractContextManager[Connection]]:
    """Provide a migration context entered inside each test, not during setup.

    Args:
        database_engine: Existing fixture restricted to the local test database.

    Returns:
        A context factory applying the initial revision and cleaning owned tables.
    """
    @contextmanager
    def apply_initial_migration() -> Iterator[Connection]:
        """Apply the revision to an unoccupied schema and yield its connection.

        Yields:
            A connection for assertions and rollback-only test row operations.

        Raises:
            AssertionError: A revision is absent or pre-existing targets are found.
            Exception: Migration or cleanup fails; errors are never suppressed.
        """
        assert INITIAL_MIGRATION.is_file(), "T015 must provide 001_initial_schema.py"
        with database_engine.connect() as connection:
            before = set(inspect(connection).get_table_names())
            before_views = set(inspect(connection).get_view_names())
            conflicts = (before | before_views).intersection(SCHEMA_DROP_ORDER)
            assert not conflicts, f"{RECOVERY_HINT} Found: {sorted(conflicts)}"
            connection.rollback()

            spec = importlib.util.spec_from_file_location("t012_initial_revision", INITIAL_MIGRATION)
            assert spec is not None and spec.loader is not None
            revision = importlib.util.module_from_spec(spec)
            # Include module execution in cleanup in case an invalid revision
            # performs DDL while being imported. Only known new targets are owned.
            try:
                spec.loader.exec_module(revision)
                assert callable(getattr(revision, "upgrade", None)), "Revision requires upgrade()"
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    revision.upgrade()
                connection.commit()
                yield connection
            finally:
                connection.rollback()
                remaining = set(inspect(connection).get_table_names())
                connection.rollback()
                for name in SCHEMA_DROP_ORDER:
                    if name in remaining and name not in before:
                        connection.execute(text(f"DROP TABLE `{name}`"))
                connection.commit()
                after = set(inspect(connection).get_table_names())
                assert not after.intersection(SCHEMA_DROP_ORDER), "Cleanup left migration targets"
                assert before <= after, "Migration removed pre-existing unrelated tables"
                assert not (after - before), "Unexpected new tables retained; inspect manually"

    return apply_initial_migration


@pytest.mark.parametrize("table_name, primary_key", EXPECTED_PRIMARY_KEYS)
def test_migration_table_structure(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
    table_name: str,
    primary_key: tuple[str, ...],
) -> None:
    """Verify real table names, columns, primary keys and InnoDB storage.

    Args:
        migrated_schema: Context applying the revision to the test database.
        table_name: Table required by the independent design contract.
        primary_key: Ordered primary-key column names from the design.
    """
    with migrated_schema() as connection:
        inspector = inspect(connection)
        assert set(inspector.get_table_names()) == set(EXPECTED_COLUMNS)
        assert {column["name"] for column in inspector.get_columns(table_name)} == EXPECTED_COLUMNS[table_name]
        assert tuple(inspector.get_pk_constraint(table_name)["constrained_columns"]) == primary_key
        assert inspector.get_table_options(table_name)["mysql_engine"] == "InnoDB"


def test_migration_guard_seed(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
) -> None:
    """Verify the migration itself inserts exactly the fixed guard row.

    Args:
        migrated_schema: Context applying the revision without adding test rows.
    """
    with migrated_schema() as connection:
        assert list(connection.scalars(text("SELECT id FROM lineage_mutation_guard"))) == [1]


@pytest.mark.parametrize("table_name", EXPECTED_COLUMNS)
def test_migration_matches_validated_model_columns_and_constraints(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
    table_name: str,
) -> None:
    """Detect drift between the independently tested model and migrated schema.

    Args:
        migrated_schema: Context applying the initial revision.
        table_name: Product table to reflect from MySQL.
    """
    expected = require_table(table_name)
    with migrated_schema() as connection:
        reflected = MetaData()
        reflected.reflect(bind=connection)
        actual = reflected.tables[table_name]
        for column in expected.columns:
            stored = actual.c[column.name]
            assert stored.nullable == column.nullable, column.name
            assert stored.type.compile(dialect=mysql.dialect()) == column.type.compile(dialect=mysql.dialect()), column.name
            assert {key.target_fullname for key in stored.foreign_keys} == {
                key.target_fullname for key in column.foreign_keys
            }, column.name
        inspector = inspect(connection)
        actual_unique = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints(table_name)
        }
        expected_unique = {
            tuple(constraint.columns.keys()) for constraint in expected.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        expected_unique.update(
            tuple(index.columns.keys()) for index in expected.indexes if index.unique
        )
        assert actual_unique == expected_unique


def test_migration_search_indexes(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
) -> None:
    """Verify non-unique index order and direction using MySQL's catalog.

    Args:
        migrated_schema: Context applying the initial revision.
    """
    with migrated_schema() as connection:
        rows = connection.execute(text(
            "SELECT INDEX_NAME, COLUMN_NAME, COLLATION FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='evolution_step' AND NON_UNIQUE=1 "
            "ORDER BY INDEX_NAME, SEQ_IN_INDEX"
        ))
        indexes: dict[str, list[tuple[str, str]]] = {}
        for index_name, column_name, direction in rows:
            indexes.setdefault(index_name, []).append((column_name, direction))
        assert [("parent_run_id", "A")] in indexes.values()
        assert [("created_at", "D"), ("id", "D")] in indexes.values()


def insert_reference(connection: Connection, run_id: str) -> None:
    """Insert a valid reference as preparation for DB constraint checks.

    Args:
        connection: Connection with an active rollback-only test transaction.
        run_id: Identifier to make available as a foreign-key target.
    """
    connection.execute(text(
        "INSERT INTO run_reference (run_id, current_status, last_synced_at, created_at) "
        "VALUES (:run_id, 'RUNNING', :now, :now)"
    ), {"run_id": run_id, "now": SAMPLE_TIME})


def insert_step(
    connection: Connection, step_id: int, parent: str | None, result: str | None,
) -> None:
    """Insert a step without relying on the unimplemented model or repository.

    Args:
        connection: Active test connection.
        step_id: Unique test step identifier.
        parent: Optional parent reference identifier.
        result: Optional result reference identifier.
    """
    connection.execute(text(
        "INSERT INTO evolution_step "
        "(id, purpose, hypothesis, parent_run_id, result_run_id, created_at, updated_at) "
        "VALUES (:id, 'improve', 'test hypothesis', :parent, :result, :now, :now)"
    ), {"id": step_id, "parent": parent, "result": result, "now": SAMPLE_TIME})


def test_migration_allows_shared_parent_and_null_results(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
) -> None:
    """Accept shared parents and multiple NULL results without uniqueness conflicts.

    Args:
        migrated_schema: Context applying the initial revision.
    """
    with migrated_schema() as connection, connection.begin():
        insert_reference(connection, "run-001")
        insert_reference(connection, "run-002")
        insert_reference(connection, "run-003")
        insert_step(connection, 10, "run-001", "run-002")
        insert_step(connection, 20, "run-001", "run-003")
        insert_step(connection, 30, None, None)
        insert_step(connection, 40, None, None)
        assert connection.scalar(text("SELECT COUNT(*) FROM evolution_step")) == 4
        connection.rollback()


@pytest.mark.parametrize("case, mysql_error", [
    ("duplicate_result", 1062),
    ("duplicate_primary_key", 1062),
    ("missing_parent", 1452),
    ("missing_result", 1452),
    ("null_purpose", 1048),
    ("null_hypothesis", 1048),
])
def test_migration_rejects_invalid_step_rows(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
    case: str,
    mysql_error: int,
) -> None:
    """Require real constraint violations, not unrelated preparation failures.

    Args:
        migrated_schema: Context applying the initial revision.
        case: Invalid write to attempt after valid preparation.
        mysql_error: MySQL error code identifying the intended constraint class.
    """
    with migrated_schema() as connection, connection.begin():
        insert_reference(connection, "run-001")
        insert_step(connection, 10, None, "run-001")
        with pytest.raises(IntegrityError) as caught:
            if case == "duplicate_result":
                insert_step(connection, 20, None, "run-001")
            elif case == "duplicate_primary_key":
                insert_step(connection, 10, None, None)
            elif case == "missing_parent":
                insert_step(connection, 20, "missing", None)
            elif case == "missing_result":
                insert_step(connection, 20, None, "missing")
            else:
                column = "purpose" if case == "null_purpose" else "hypothesis"
                connection.execute(text(f"UPDATE evolution_step SET {column}=NULL WHERE id=10"))
        assert caught.value.orig.args[0] == mysql_error
        connection.rollback()


def test_migration_snapshot_signed_step_and_datetime_round_trip(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
) -> None:
    """Round-trip negative and large signed steps and microsecond timestamps.

    Args:
        migrated_schema: Context applying the initial revision.
    """
    with migrated_schema() as connection, connection.begin():
        for number, step in enumerate([-1, -(2**63), 2**63 - 1]):
            run_id = f"run-{number}"
            insert_reference(connection, run_id)
            connection.execute(text(
                "INSERT INTO run_snapshot "
                "(run_id, status_at_capture, best_accuracy, best_accuracy_step, "
                "best_accuracy_recorded_at, captured_at) "
                "VALUES (:run_id, 'FINISHED', 0.9, :step, :now, :now)"
            ), {"run_id": run_id, "step": step, "now": SAMPLE_TIME})
            connection.execute(text(
                "INSERT INTO best_step_metric (run_id, name, value, step, recorded_at) "
                "VALUES (:run_id, 'accuracy', 0.9, :step, :now)"
            ), {"run_id": run_id, "step": step, "now": SAMPLE_TIME})
            actual = connection.execute(text(
                "SELECT s.best_accuracy_step, m.step, s.captured_at, m.recorded_at "
                "FROM run_snapshot s JOIN best_step_metric m ON s.run_id=m.run_id "
                "WHERE s.run_id=:run_id"
            ), {"run_id": run_id}).one()
            assert tuple(actual) == (step, step, SAMPLE_TIME, SAMPLE_TIME)
        connection.rollback()


@pytest.mark.parametrize("case, mysql_error", [
    ("snapshot_duplicate", 1062),
    ("snapshot_missing_reference", 1452),
    ("parameter_duplicate", 1062),
    ("parameter_missing_snapshot", 1452),
    ("metric_duplicate", 1062),
    ("metric_missing_snapshot", 1452),
    ("dataset_duplicate_ordinal", 1062),
    ("dataset_missing_snapshot", 1452),
    ("history_missing_step", 1452),
])
def test_migration_rejects_invalid_child_rows(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
    case: str,
    mysql_error: int,
) -> None:
    """Exercise snapshot ownership and normalized child-table constraints.

    Args:
        migrated_schema: Context applying the initial revision.
        case: Duplicate or missing-reference write to attempt.
        mysql_error: Expected MySQL constraint error code.
    """
    statements = {
        "snapshot": (
            "INSERT INTO run_snapshot (run_id, status_at_capture, captured_at) "
            "VALUES (:run_id, 'FINISHED', :now)"
        ),
        "parameter": "INSERT INTO run_parameter (run_id, name, value) VALUES (:run_id, 'epochs', '10')",
        "metric": (
            "INSERT INTO best_step_metric (run_id, name, value, step, recorded_at) "
            "VALUES (:run_id, 'accuracy', 0.9, 1, :now)"
        ),
        "dataset": (
            "INSERT INTO dataset_input (id, run_id, ordinal, name, digest, source_type, source) "
            "VALUES (:id, :run_id, 0, 'training', 'abc', 'local', 'training.csv')"
        ),
        "history": (
            "INSERT INTO evolution_step_history (id, evolution_step_id, field, changed_at) "
            "VALUES (1, 999, 'purpose', :now)"
        ),
    }
    with migrated_schema() as connection, connection.begin():
        insert_reference(connection, "run-001")
        parameters = {"run_id": "run-001", "now": SAMPLE_TIME, "id": 1}
        connection.execute(text(statements["snapshot"]), parameters)
        for child in ("parameter", "metric", "dataset"):
            connection.execute(text(statements[child]), parameters)
        target = case.split("_", maxsplit=1)[0]
        invalid = {**parameters, "id": 2}
        if "missing" in case:
            invalid["run_id"] = "missing"
        with pytest.raises(IntegrityError) as caught:
            connection.execute(text(statements[target]), invalid)
        assert caught.value.orig.args[0] == mysql_error
        connection.rollback()


@pytest.fixture
def probe_revision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Supply a disposable revision solely to verify the test harness itself.

    Args:
        tmp_path: Pytest's temporary directory, not the production migration tree.
        monkeypatch: Restores the initial revision path after this test.

    Returns:
        Path of a minimal revision creating only the known guard table.
    """
    path = tmp_path / "probe_revision.py"
    path.write_text(
        'from alembic import op\n'
        'import sqlalchemy as sa\n\n'
        'def upgrade() -> None:\n'
        '    """Create one disposable table for harness verification."""\n'
        '    op.create_table("lineage_mutation_guard", sa.Column("id", sa.Integer(), primary_key=True))\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(sys.modules[__name__], "INITIAL_MIGRATION", path)
    return path


def test_migration_harness_cleans_after_success(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
    database_engine: Engine,
    probe_revision: Path,
) -> None:
    """Verify a successful revision is applied and its table is cleaned up.

    Args:
        migrated_schema: Context under test.
        database_engine: Dedicated test engine for independent observations.
        probe_revision: Disposable revision selected by the fixture.
    """
    with migrated_schema() as connection:
        assert "lineage_mutation_guard" in inspect(connection).get_table_names()
    assert "lineage_mutation_guard" not in inspect(database_engine).get_table_names()


def test_migration_harness_cleans_after_upgrade_failure(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
    database_engine: Engine,
    probe_revision: Path,
) -> None:
    """Verify cleanup covers partial DDL before upgrade raises an exception.

    Args:
        migrated_schema: Context under test.
        database_engine: Dedicated engine for observing cleanup.
        probe_revision: Temporary revision extended with an intentional failure.
    """
    with probe_revision.open("a", encoding="utf-8") as output:
        output.write('    raise RuntimeError("probe upgrade failed")\n')
    with pytest.raises(RuntimeError, match="probe upgrade failed"), migrated_schema():
        pytest.fail("Failed upgrade must not yield a connection")
    assert "lineage_mutation_guard" not in inspect(database_engine).get_table_names()


def test_migration_harness_cleans_after_test_failure(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
    database_engine: Engine,
    probe_revision: Path,
) -> None:
    """Verify failed test assertions cannot bypass schema teardown.

    Args:
        migrated_schema: Context under test.
        database_engine: Dedicated engine for observing cleanup.
        probe_revision: Disposable revision selected by the fixture.
    """
    with pytest.raises(AssertionError, match="probe assertion"), migrated_schema():
        raise AssertionError("probe assertion")
    assert "lineage_mutation_guard" not in inspect(database_engine).get_table_names()


def test_migration_harness_preserves_existing_target(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
    database_engine: Engine,
    probe_revision: Path,
) -> None:
    """Reject an occupied target before migration without deleting its data.

    Args:
        migrated_schema: Context expected to reject the simulated existing table.
        database_engine: Dedicated engine preparing an owned sentinel table.
        probe_revision: Revision which must never execute in this case.
    """
    inspector = inspect(database_engine)
    assert "lineage_mutation_guard" not in set(inspector.get_table_names()) | set(inspector.get_view_names()), RECOVERY_HINT
    with database_engine.begin() as connection:
        connection.execute(text("CREATE TABLE lineage_mutation_guard (id INT PRIMARY KEY) ENGINE=InnoDB"))
    try:
        with database_engine.begin() as connection:
            connection.execute(text("INSERT INTO lineage_mutation_guard (id) VALUES (77)"))
        with pytest.raises(AssertionError, match="Existing migration targets"), migrated_schema():
            pytest.fail("Existing targets must be rejected")
        with database_engine.connect() as connection:
            assert list(connection.scalars(text("SELECT id FROM lineage_mutation_guard"))) == [77]
    finally:
        # This outer test created the sentinel; the migration context must not.
        with database_engine.begin() as connection:
            connection.execute(text("DROP TABLE lineage_mutation_guard"))


def test_migration_harness_preserves_unrelated_table(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
    database_engine: Engine,
    probe_revision: Path,
    probe_table: Table,
) -> None:
    """Leave an unrelated T010 fixture table intact after migration cleanup.

    Args:
        migrated_schema: Context under test.
        database_engine: Dedicated engine for observing preserved tables.
        probe_revision: Disposable revision creating the guard table.
        probe_table: Independently owned temporary table from the T010 fixture.
    """
    with migrated_schema():
        assert probe_table.name in inspect(database_engine).get_table_names()
    assert probe_table.name in inspect(database_engine).get_table_names()
