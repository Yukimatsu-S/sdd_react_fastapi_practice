"""Mondel's table definitions; importing this module does not connect to MySQL.

Alembic applies this design to the database in T014-T015. Business validation,
timestamps and snapshot immutability remain explicit service responsibilities.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME, DOUBLE, JSON, LONGTEXT, TINYINT

metadata = MetaData()

run_reference = Table(
    "run_reference",
    metadata,
    Column("run_id", String(64), primary_key=True),
    Column("mlflow_experiment_id", String(64), nullable=True),
    Column("run_name", String(255), nullable=True),
    Column("current_status", String(16), nullable=False),
    Column("started_at", DATETIME(fsp=6), nullable=True),
    Column("ended_at", DATETIME(fsp=6), nullable=True),
    Column("last_synced_at", DATETIME(fsp=6), nullable=False),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_0900_bin",
)

evolution_step = Table(
    "evolution_step",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("purpose", Text, nullable=False),
    Column("hypothesis", Text, nullable=False),
    Column("change_description", Text, nullable=True),
    Column("parent_run_id", String(64), ForeignKey("run_reference.run_id"), nullable=True),
    Column("result_run_id", String(64), ForeignKey("run_reference.run_id"), nullable=True),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    Column("updated_at", DATETIME(fsp=6), nullable=False),
    UniqueConstraint("result_run_id", name="uq_evolution_step_result_run_id"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_0900_bin",
)
Index("ix_evolution_step_parent_run_id", evolution_step.c.parent_run_id)
Index("ix_evolution_step_created_id", evolution_step.c.created_at.desc(), evolution_step.c.id.desc())

# The migration inserts id=1; importing this definition does not insert rows.
lineage_mutation_guard = Table(
    "lineage_mutation_guard",
    metadata,
    Column("id", TINYINT, primary_key=True, autoincrement=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_0900_bin",
)

run_snapshot = Table(
    "run_snapshot",
    metadata,
    Column("run_id", String(64), ForeignKey("run_reference.run_id"), primary_key=True),
    Column("status_at_capture", String(16), nullable=False),
    Column("started_at", DATETIME(fsp=6), nullable=True),
    Column("ended_at", DATETIME(fsp=6), nullable=True),
    Column("best_accuracy", DOUBLE, nullable=True),
    Column("best_accuracy_step", BigInteger, nullable=True),
    Column("best_accuracy_recorded_at", DATETIME(fsp=6), nullable=True),
    Column("captured_at", DATETIME(fsp=6), nullable=False),
    Column("raw_metadata", JSON(none_as_null=True), nullable=True),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_0900_bin",
)

run_parameter = Table(
    "run_parameter",
    metadata,
    Column("run_id", String(64), ForeignKey("run_snapshot.run_id"), primary_key=True),
    Column("name", String(250), primary_key=True),
    Column("value", Text, nullable=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_0900_bin",
)

best_step_metric = Table(
    "best_step_metric",
    metadata,
    Column("run_id", String(64), ForeignKey("run_snapshot.run_id"), primary_key=True),
    Column("name", String(250), primary_key=True),
    Column("value", DOUBLE, nullable=False),
    Column("step", BigInteger, nullable=False),
    Column("recorded_at", DATETIME(fsp=6), nullable=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_0900_bin",
)

dataset_input = Table(
    "dataset_input",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("run_id", String(64), ForeignKey("run_snapshot.run_id"), nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("name", LONGTEXT, nullable=False),
    Column("digest", LONGTEXT, nullable=False),
    Column("source_type", LONGTEXT, nullable=False),
    Column("source", LONGTEXT, nullable=False),
    Column("schema", LONGTEXT, nullable=True),
    Column("profile", LONGTEXT, nullable=True),
    Column("context", LONGTEXT, nullable=True),
    Column("raw_metadata", JSON(none_as_null=True), nullable=True),
    UniqueConstraint("run_id", "ordinal", name="uq_dataset_input_run_ordinal"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_0900_bin",
)

evolution_step_history = Table(
    "evolution_step_history",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("evolution_step_id", BigInteger, ForeignKey("evolution_step.id"), nullable=False),
    Column("field", Enum(
        "purpose", "hypothesis", "change_description", "parent_run_id", "result_run_id",
        name="evolution_step_history_field", native_enum=True,
    ), nullable=False),
    Column("old_value", Text, nullable=True),
    Column("new_value", Text, nullable=True),
    Column("changed_at", DATETIME(fsp=6), nullable=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_0900_bin",
)
