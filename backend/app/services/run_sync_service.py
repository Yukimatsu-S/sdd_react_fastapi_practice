"""Synchronize mutable Run metadata and capture terminal Snapshots once."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.engine import Connection

from app.domain.run_snapshot import select_best_step_metrics
from app.infrastructure.mlflow_gateway import LoadedRun, RunLoaderGateway
from app.infrastructure.run_repository import (
    BestStepMetricRecord,
    DatasetInputRecord,
    RunReferenceRecord,
    RunRepository,
    RunSnapshotRecord,
)


@dataclass(frozen=True)
class RunSyncResult:
    """Current Reference and optional immutable Snapshot after synchronization."""

    reference: RunReferenceRecord
    snapshot: RunSnapshotRecord | None


class RunSyncService:
    """Save current MLflow metadata and capture terminal data at most once."""

    def __init__(self, connection: Connection, run_loader: RunLoaderGateway) -> None:
        """Store the dependencies for one synchronous Run update.

        Args:
            connection: Connection used for the database transaction.
            run_loader: Gateway used to read current MLflow data.
        """
        self._connection = connection
        self._run_loader = run_loader

    def sync(self, run_id: str, now: datetime) -> RunSyncResult:
        """Synchronize one Run and capture terminal data only when still pending.

        Args:
            run_id: MLflow Run identifier to refresh.
            now: UTC time at which the synchronization completed.

        Returns:
            RunSyncResult: Updated mutable Reference and optional immutable Snapshot.
        """
        loaded_run = self._run_loader.load(run_id)
        with self._connection.begin():
            repository = RunRepository(self._connection)
            reference = repository.upsert_reference(_to_reference_record(loaded_run, now))
            snapshot = repository.get_snapshot(run_id)
            if snapshot is None and loaded_run.snapshot_payload is not None:
                snapshot = repository.capture_snapshot(
                    _to_snapshot_record(loaded_run, now),
                )
            return RunSyncResult(reference=reference, snapshot=snapshot)


def _to_reference_record(loaded_run: LoadedRun, synced_at: datetime) -> RunReferenceRecord:
    """Map current MLflow fields to mutable Run Reference storage fields.

    Args:
        loaded_run: Current data returned by the MLflow gateway.
        synced_at: UTC timestamp of this successful synchronization.

    Returns:
        RunReferenceRecord: Current metadata ready for persistence.
    """
    return RunReferenceRecord(
        run_id=loaded_run.run_id,
        mlflow_experiment_id=loaded_run.mlflow_experiment_id,
        run_name=loaded_run.run_name,
        current_status=loaded_run.status,
        started_at=loaded_run.started_at,
        ended_at=loaded_run.ended_at,
        last_synced_at=synced_at,
        created_at=synced_at,
    )


def _to_snapshot_record(loaded_run: LoadedRun, captured_at: datetime) -> RunSnapshotRecord:
    """Select a terminal Run's best-step Metric data for immutable storage.

    Args:
        loaded_run: Terminal Run with a gateway-provided Snapshot payload.
        captured_at: UTC timestamp at which this Snapshot is first stored.

    Returns:
        RunSnapshotRecord: Immutable Snapshot and all of its child records.

    Raises:
        ValueError: If called for a Run without terminal Snapshot payload data.
    """
    payload = loaded_run.snapshot_payload
    if payload is None:
        raise ValueError("terminal Snapshot payload is required")

    selection = select_best_step_metrics(payload.metrics)
    return RunSnapshotRecord(
        run_id=loaded_run.run_id,
        status_at_capture=loaded_run.status,
        started_at=loaded_run.started_at,
        ended_at=loaded_run.ended_at,
        best_accuracy=selection.best_accuracy,
        best_accuracy_step=selection.best_accuracy_step,
        best_accuracy_recorded_at=selection.best_accuracy_recorded_at,
        captured_at=captured_at,
        parameters=payload.parameters,
        metrics=tuple(
            BestStepMetricRecord(
                name=metric.name,
                value=metric.value,
                step=metric.step,
                recorded_at=metric.recorded_at,
            )
            for metric in selection.metrics
        ),
        datasets=tuple(
            DatasetInputRecord(
                ordinal=ordinal,
                name=dataset.name,
                digest=dataset.digest,
                source_type=dataset.source_type,
                source=dataset.source,
                schema=dataset.schema,
                profile=dataset.profile,
                context=dataset.context,
            )
            for ordinal, dataset in enumerate(payload.datasets)
        ),
    )
