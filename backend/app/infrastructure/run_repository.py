"""SQLAlchemy Core persistence for Run References and immutable Snapshots."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.engine import Connection

from app.infrastructure.models import (
    best_step_metric,
    dataset_input,
    run_parameter,
    run_reference,
    run_snapshot,
)


@dataclass(frozen=True)
class RunReferenceRecord:
    """Current mutable metadata for one MLflow Run."""

    run_id: str
    mlflow_experiment_id: str | None
    run_name: str | None
    current_status: str
    started_at: datetime | None
    ended_at: datetime | None
    last_synced_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class BestStepMetricRecord:
    """One Metric retained at the selected best-accuracy step."""

    name: str
    value: float
    step: int
    recorded_at: datetime


@dataclass(frozen=True)
class DatasetInputRecord:
    """One Dataset Input retained in an immutable Snapshot."""

    ordinal: int
    name: str
    digest: str
    source_type: str
    source: str
    schema: str | None = None
    profile: str | None = None
    context: str | None = None


@dataclass(frozen=True)
class RunSnapshotRecord:
    """One finalized Run Snapshot together with its captured child records."""

    run_id: str
    status_at_capture: str
    started_at: datetime | None
    ended_at: datetime | None
    best_accuracy: float | None
    best_accuracy_step: int | None
    best_accuracy_recorded_at: datetime | None
    captured_at: datetime
    parameters: dict[str, str]
    metrics: tuple[BestStepMetricRecord, ...]
    datasets: tuple[DatasetInputRecord, ...]


class RunRepository:
    """Save mutable Run References and retain the first terminal Snapshot."""

    def __init__(self, connection: Connection) -> None:
        """Store the transaction-owned connection used for all repository calls.

        Args:
            connection: Open connection owned by the caller's transaction.
        """
        self._connection = connection

    def upsert_reference(self, record: RunReferenceRecord) -> RunReferenceRecord:
        """Insert a new reference or refresh only its mutable current fields.

        Args:
            record: Current MLflow metadata for one Run.

        Returns:
            RunReferenceRecord: Reference as persisted after the insert or update.
        """
        existing = self._connection.execute(
            select(run_reference.c.run_id).where(run_reference.c.run_id == record.run_id),
        ).scalar_one_or_none()
        if existing is None:
            self._connection.execute(run_reference.insert().values(**record.__dict__))
        else:
            self._connection.execute(
                update(run_reference)
                .where(run_reference.c.run_id == record.run_id)
                .values(
                    mlflow_experiment_id=record.mlflow_experiment_id,
                    run_name=record.run_name,
                    current_status=record.current_status,
                    started_at=record.started_at,
                    ended_at=record.ended_at,
                    last_synced_at=record.last_synced_at,
                ),
            )
        return self._get_reference(record.run_id)

    def get_snapshot(self, run_id: str) -> RunSnapshotRecord | None:
        """Read a captured Snapshot or return ``None`` while it is pending.

        Args:
            run_id: Run identifier whose Snapshot is requested.

        Returns:
            RunSnapshotRecord | None: Immutable captured data, if present.
        """
        snapshot_row = self._connection.execute(
            select(run_snapshot).where(run_snapshot.c.run_id == run_id),
        ).mappings().one_or_none()
        if snapshot_row is None:
            return None

        parameters = dict(
            self._connection.execute(
                select(run_parameter.c.name, run_parameter.c.value)
                .where(run_parameter.c.run_id == run_id)
                .order_by(run_parameter.c.name.asc()),
            ).all(),
        )
        metrics = tuple(
            BestStepMetricRecord(
                name=str(row["name"]),
                value=float(row["value"]),
                step=int(row["step"]),
                recorded_at=row["recorded_at"],
            )
            for row in self._connection.execute(
                select(best_step_metric)
                .where(best_step_metric.c.run_id == run_id)
                .order_by(best_step_metric.c.name.asc()),
            ).mappings()
        )
        datasets = tuple(
            DatasetInputRecord(
                ordinal=int(row["ordinal"]),
                name=str(row["name"]),
                digest=str(row["digest"]),
                source_type=str(row["source_type"]),
                source=str(row["source"]),
                schema=row["schema"],
                profile=row["profile"],
                context=row["context"],
            )
            for row in self._connection.execute(
                select(dataset_input)
                .where(dataset_input.c.run_id == run_id)
                .order_by(dataset_input.c.ordinal.asc()),
            ).mappings()
        )
        return _to_snapshot_record(snapshot_row, parameters, metrics, datasets)

    def capture_snapshot(self, record: RunSnapshotRecord) -> RunSnapshotRecord:
        """Persist the first terminal Snapshot and reuse it on later calls.

        The caller owns the surrounding transaction. A child-insert failure can
        therefore roll back the Snapshot row and every child row together.

        Args:
            record: Terminal Run data prepared for immutable capture.

        Returns:
            RunSnapshotRecord: First captured data for the requested Run.
        """
        existing = self.get_snapshot(record.run_id)
        if existing is not None:
            return existing

        self._connection.execute(
            run_snapshot.insert().values(
                run_id=record.run_id,
                status_at_capture=record.status_at_capture,
                started_at=record.started_at,
                ended_at=record.ended_at,
                best_accuracy=record.best_accuracy,
                best_accuracy_step=record.best_accuracy_step,
                best_accuracy_recorded_at=record.best_accuracy_recorded_at,
                captured_at=record.captured_at,
            ),
        )
        self._connection.execute(
            run_parameter.insert(),
            [
                {"run_id": record.run_id, "name": name, "value": value}
                for name, value in record.parameters.items()
            ],
        )
        self._connection.execute(
            best_step_metric.insert(),
            [
                {
                    "run_id": record.run_id,
                    "name": metric.name,
                    "value": metric.value,
                    "step": metric.step,
                    "recorded_at": metric.recorded_at,
                }
                for metric in record.metrics
            ],
        )
        self._connection.execute(
            dataset_input.insert(),
            [
                {
                    "run_id": record.run_id,
                    "ordinal": dataset.ordinal,
                    "name": dataset.name,
                    "digest": dataset.digest,
                    "source_type": dataset.source_type,
                    "source": dataset.source,
                    "schema": dataset.schema,
                    "profile": dataset.profile,
                    "context": dataset.context,
                }
                for dataset in record.datasets
            ],
        )
        return record

    def _get_reference(self, run_id: str) -> RunReferenceRecord:
        """Read one stored Run Reference after a successful mutation.

        Args:
            run_id: Identifier of the reference just inserted or refreshed.

        Returns:
            RunReferenceRecord: Stored mutable reference data.
        """
        row = self._connection.execute(
            select(run_reference).where(run_reference.c.run_id == run_id),
        ).mappings().one()
        return RunReferenceRecord(
            run_id=str(row["run_id"]),
            mlflow_experiment_id=row["mlflow_experiment_id"],
            run_name=row["run_name"],
            current_status=str(row["current_status"]),
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            last_synced_at=row["last_synced_at"],
            created_at=row["created_at"],
        )


def _to_snapshot_record(
    row: Mapping[str, object],
    parameters: dict[str, str],
    metrics: tuple[BestStepMetricRecord, ...],
    datasets: tuple[DatasetInputRecord, ...],
) -> RunSnapshotRecord:
    """Convert one Snapshot row and child rows to public immutable data.

    Args:
        row: Row from ``run_snapshot`` including private raw metadata.
        parameters: Captured Parameter name/value pairs.
        metrics: Metrics retained at the selected best step.
        datasets: Captured Dataset Inputs in ordinal order.

    Returns:
        RunSnapshotRecord: Public Snapshot data without raw metadata.
    """
    return RunSnapshotRecord(
        run_id=str(row["run_id"]),
        status_at_capture=str(row["status_at_capture"]),
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        best_accuracy=None if row["best_accuracy"] is None else float(row["best_accuracy"]),
        best_accuracy_step=None if row["best_accuracy_step"] is None else int(row["best_accuracy_step"]),
        best_accuracy_recorded_at=row["best_accuracy_recorded_at"],
        captured_at=row["captured_at"],
        parameters=parameters,
        metrics=metrics,
        datasets=datasets,
    )
