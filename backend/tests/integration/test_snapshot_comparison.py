"""Specify two-Run comparison reads from immutable persisted Snapshots."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime

from sqlalchemy.engine import Connection

from app.infrastructure.evolution_step_repository import EvolutionStepRepository
from app.infrastructure.run_repository import (
    DatasetInputRecord,
    RunReferenceRecord,
    RunRepository,
    RunSnapshotRecord,
)
from app.services.comparison_service import ComparisonService

TIME = datetime(2026, 9, 18, 13, 0, tzinfo=UTC).replace(tzinfo=None)
SYNCED_TIME = datetime(2026, 9, 18, 14, 0, tzinfo=UTC).replace(tzinfo=None)


def _reference(run_id: str, run_name: str, status: str, synced_at: datetime) -> RunReferenceRecord:
    """Create mutable Run Reference data for one integration-test Run.

    Args:
        run_id: Locally stored MLflow Run ID.
        run_name: Latest display name returned by MLflow.
        status: Latest current MLflow status.
        synced_at: Time at which the reference metadata was refreshed.

    Returns:
        RunReferenceRecord: Current metadata record ready for persistence.
    """
    return RunReferenceRecord(
        run_id=run_id,
        mlflow_experiment_id="mlflow-experiment-1",
        run_name=run_name,
        current_status=status,
        started_at=TIME,
        ended_at=SYNCED_TIME if status == "FINISHED" else None,
        last_synced_at=synced_at,
        created_at=TIME,
    )


def _snapshot(
    run_id: str,
    parameters: dict[str, str],
    best_accuracy: float,
    datasets: tuple[DatasetInputRecord, ...],
) -> RunSnapshotRecord:
    """Create finalized immutable data used by a comparison integration test.

    Args:
        run_id: Run ID that owns this captured Snapshot.
        parameters: Captured Parameter name/value pairs.
        best_accuracy: Captured best accuracy ratio.
        datasets: Captured Dataset Inputs.

    Returns:
        RunSnapshotRecord: Terminal Snapshot without unrelated Metric rows.
    """
    return RunSnapshotRecord(
        run_id=run_id,
        status_at_capture="FINISHED",
        started_at=TIME,
        ended_at=SYNCED_TIME,
        best_accuracy=best_accuracy,
        best_accuracy_step=5,
        best_accuracy_recorded_at=SYNCED_TIME,
        captured_at=SYNCED_TIME,
        parameters=parameters,
        metrics=(),
        datasets=datasets,
    )


def test_comparison_reads_finalized_snapshots_not_mutable_run_reference_metadata(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
) -> None:
    """Keep persisted comparison results stable after only reference metadata changes."""
    with migrated_schema() as connection:
        runs = RunRepository(connection)
        steps = EvolutionStepRepository(connection)
        runs.upsert_reference(_reference("run-parent", "baseline-v1", "FINISHED", TIME))
        runs.upsert_reference(_reference("run-result", "candidate-v1", "FINISHED", TIME))
        runs.capture_snapshot(
            _snapshot(
                "run-parent",
                {"epochs": "10", "learning_rate": "0.01"},
                0.90,
                (DatasetInputRecord(0, "images", "digest-v1", "s3", "s3://data/v1", context="train"),),
            ),
        )
        runs.capture_snapshot(
            _snapshot(
                "run-result",
                {"epochs": "20", "optimizer": "adamw"},
                0.92,
                (DatasetInputRecord(0, "images", "digest-v2", "s3", "s3://data/v2", context="train"),),
            ),
        )
        step = steps.create(
            purpose="accuracy improvement",
            hypothesis="more epochs improve accuracy",
            change_description=None,
            parent_run_id="run-parent",
            result_run_id="run-result",
            now=TIME,
        )
        connection.commit()

        service = ComparisonService(connection)
        before_sync = service.get(step.id)

        runs.upsert_reference(_reference("run-parent", "baseline-renamed", "KILLED", SYNCED_TIME))
        runs.upsert_reference(_reference("run-result", "candidate-renamed", "FAILED", SYNCED_TIME))
        connection.commit()
        after_sync = service.get(step.id)

    assert before_sync == after_sync
    assert before_sync.status == "available"
    assert [(item.name, item.status) for item in before_sync.parameters] == [
        ("epochs", "changed"),
        ("learning_rate", "removed"),
        ("optimizer", "added"),
    ]
    assert before_sync.accuracy.parent_best == 0.90
    assert before_sync.accuracy.result_best == 0.92
    assert before_sync.accuracy.delta == 0.02
    assert before_sync.datasets.status == "changed"
    assert before_sync.datasets.differences[0].changed_fields == ("digest", "source")
