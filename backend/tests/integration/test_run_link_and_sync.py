"""Specify Run Reference and immutable terminal Snapshot persistence."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime

from sqlalchemy.engine import Connection

from app.domain.run_snapshot import MetricObservation
from app.infrastructure.mlflow_gateway import LoadedRun, RunSnapshotPayload
from app.infrastructure.run_repository import (
    BestStepMetricRecord,
    DatasetInputRecord,
    RunReferenceRecord,
    RunRepository,
    RunSnapshotRecord,
)
from app.services.run_sync_service import RunSyncService

TIME = datetime(2026, 9, 18, 11, 0, tzinfo=UTC).replace(tzinfo=None)
LATER_TIME = datetime(2026, 9, 18, 12, 0, tzinfo=UTC).replace(tzinfo=None)


class SequencedRunLoader:
    """Return current Run data in the order configured by this integration test."""

    def __init__(self, runs: list[LoadedRun]) -> None:
        """Store the Run states returned by consecutive synchronization calls.

        Args:
            runs: MLflow-derived states from active through terminal.
        """
        self._runs = iter(runs)

    def load(self, run_id: str) -> LoadedRun:
        """Return the next state for the requested Run.

        Args:
            run_id: Identifier requested by the synchronization service.

        Returns:
            LoadedRun: Next configured current state.
        """
        return next(self._runs)


def test_repository_updates_current_reference_without_creating_active_snapshot(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
) -> None:
    """Keep a running Run as a reference until terminal data is captured."""
    with migrated_schema() as connection:
        repository = RunRepository(connection)
        saved = repository.upsert_reference(
            RunReferenceRecord(
                run_id="run-active",
                mlflow_experiment_id="experiment-1",
                run_name="baseline",
                current_status="RUNNING",
                started_at=TIME,
                ended_at=None,
                last_synced_at=TIME,
                created_at=TIME,
            ),
        )
        refreshed = repository.upsert_reference(
            RunReferenceRecord(
                run_id="run-active",
                mlflow_experiment_id="experiment-1",
                run_name="baseline-renamed",
                current_status="FINISHED",
                started_at=TIME,
                ended_at=LATER_TIME,
                last_synced_at=LATER_TIME,
                created_at=TIME,
            ),
        )

        assert saved.run_name == "baseline"
        assert refreshed.run_name == "baseline-renamed"
        assert refreshed.current_status == "FINISHED"
        assert repository.get_snapshot("run-active") is None


def test_repository_captures_terminal_snapshot_once_and_keeps_first_data(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
) -> None:
    """Retain the first finalized Snapshot even if a later sync differs."""
    with migrated_schema() as connection:
        repository = RunRepository(connection)
        repository.upsert_reference(
            RunReferenceRecord(
                run_id="run-terminal",
                mlflow_experiment_id=None,
                run_name="first-name",
                current_status="FINISHED",
                started_at=TIME,
                ended_at=LATER_TIME,
                last_synced_at=LATER_TIME,
                created_at=TIME,
            ),
        )
        first_snapshot = RunSnapshotRecord(
            run_id="run-terminal",
            status_at_capture="FINISHED",
            started_at=TIME,
            ended_at=LATER_TIME,
            best_accuracy=0.91,
            best_accuracy_step=5,
            best_accuracy_recorded_at=LATER_TIME,
            captured_at=LATER_TIME,
            parameters={"epochs": "10"},
            metrics=(BestStepMetricRecord("accuracy", 0.91, 5, LATER_TIME),),
            datasets=(DatasetInputRecord(0, "training", "v1", "s3", "s3://bucket/v1"),),
        )
        later_snapshot = RunSnapshotRecord(
            run_id="run-terminal",
            status_at_capture="FINISHED",
            started_at=TIME,
            ended_at=LATER_TIME,
            best_accuracy=0.99,
            best_accuracy_step=9,
            best_accuracy_recorded_at=LATER_TIME,
            captured_at=LATER_TIME,
            parameters={"epochs": "20"},
            metrics=(BestStepMetricRecord("accuracy", 0.99, 9, LATER_TIME),),
            datasets=(DatasetInputRecord(0, "training", "v2", "s3", "s3://bucket/v2"),),
        )

        captured = repository.capture_snapshot(first_snapshot)
        reused = repository.capture_snapshot(later_snapshot)

        assert captured == first_snapshot
        assert reused == first_snapshot
        assert repository.get_snapshot("run-terminal") == first_snapshot


def test_sync_service_keeps_active_run_pending_then_captures_terminal_data(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
) -> None:
    """Synchronize metadata before capturing the first terminal Snapshot."""
    active = LoadedRun("run-sync", "experiment-1", "training", "RUNNING", TIME, None, None)
    terminal = LoadedRun(
        "run-sync",
        "experiment-1",
        "training",
        "FINISHED",
        TIME,
        LATER_TIME,
        RunSnapshotPayload(
            parameters={"epochs": "10"},
            metrics=(MetricObservation("accuracy", 0.91, 5, LATER_TIME),),
            datasets=(),
        ),
    )
    with migrated_schema() as connection:
        service = RunSyncService(connection, SequencedRunLoader([active, terminal]))

        pending = service.sync("run-sync", TIME)
        captured = service.sync("run-sync", LATER_TIME)

        assert pending.snapshot is None
        assert captured.snapshot is not None
        assert captured.snapshot.best_accuracy == 0.91
