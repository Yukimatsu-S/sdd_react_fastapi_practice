"""initial_schema

Revision ID: 001
Revises:
Create Date: 2026-09-17 09:36:44.449401
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the initial Mondel tables and seed the lineage mutation guard."""
    op.create_table(
        "lineage_mutation_guard",
        sa.Column("id", mysql.TINYINT(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_bin",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "run_reference",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("mlflow_experiment_id", sa.String(length=64), nullable=True),
        sa.Column("run_name", sa.String(length=255), nullable=True),
        sa.Column("current_status", sa.String(length=16), nullable=False),
        sa.Column("started_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("ended_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("last_synced_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_bin",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "evolution_step",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("change_description", sa.Text(), nullable=True),
        sa.Column("parent_run_id", sa.String(length=64), nullable=True),
        sa.Column("result_run_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_run_id"],
            ["run_reference.run_id"],
        ),
        sa.ForeignKeyConstraint(
            ["result_run_id"],
            ["run_reference.run_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("result_run_id", name="uq_evolution_step_result_run_id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_bin",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_evolution_step_created_id",
        "evolution_step",
        [sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_evolution_step_parent_run_id",
        "evolution_step",
        ["parent_run_id"],
        unique=False,
    )
    op.create_table(
        "run_snapshot",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("status_at_capture", sa.String(length=16), nullable=False),
        sa.Column("started_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("ended_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("best_accuracy", mysql.DOUBLE(asdecimal=True), nullable=True),
        sa.Column("best_accuracy_step", sa.BigInteger(), nullable=True),
        sa.Column("best_accuracy_recorded_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("captured_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("raw_metadata", mysql.JSON(none_as_null=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["run_reference.run_id"],
        ),
        sa.PrimaryKeyConstraint("run_id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_bin",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "best_step_metric",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("value", mysql.DOUBLE(asdecimal=True), nullable=False),
        sa.Column("step", sa.BigInteger(), nullable=False),
        sa.Column("recorded_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["run_snapshot.run_id"],
        ),
        sa.PrimaryKeyConstraint("run_id", "name"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_bin",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "dataset_input",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("name", mysql.LONGTEXT(), nullable=False),
        sa.Column("digest", mysql.LONGTEXT(), nullable=False),
        sa.Column("source_type", mysql.LONGTEXT(), nullable=False),
        sa.Column("source", mysql.LONGTEXT(), nullable=False),
        sa.Column("schema", mysql.LONGTEXT(), nullable=True),
        sa.Column("profile", mysql.LONGTEXT(), nullable=True),
        sa.Column("context", mysql.LONGTEXT(), nullable=True),
        sa.Column("raw_metadata", mysql.JSON(none_as_null=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["run_snapshot.run_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "ordinal", name="uq_dataset_input_run_ordinal"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_bin",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "evolution_step_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("evolution_step_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "field",
            sa.Enum(
                "purpose",
                "hypothesis",
                "change_description",
                "parent_run_id",
                "result_run_id",
                name="evolution_step_history_field",
            ),
            nullable=False,
        ),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("changed_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["evolution_step_id"],
            ["evolution_step.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_bin",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "run_parameter",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["run_snapshot.run_id"],
        ),
        sa.PrimaryKeyConstraint("run_id", "name"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_bin",
        mysql_engine="InnoDB",
    )
    # Schema autogeneration does not include the required initial guard row.
    op.execute(sa.text("INSERT INTO lineage_mutation_guard (id) VALUES (1)"))


def downgrade() -> None:
    """Remove the initial schema and its data in reverse dependency order."""
    op.drop_table("run_parameter")
    op.drop_table("evolution_step_history")
    op.drop_table("dataset_input")
    op.drop_table("best_step_metric")
    op.drop_table("run_snapshot")
    op.drop_index("ix_evolution_step_parent_run_id", table_name="evolution_step")
    op.drop_index("ix_evolution_step_created_id", table_name="evolution_step")
    op.drop_table("evolution_step")
    op.drop_table("run_reference")
    op.drop_table("lineage_mutation_guard")
