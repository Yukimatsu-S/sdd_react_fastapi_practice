"""Synchronous HTTP routes for MLflow Run search and local synchronization."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from mlflow import MlflowClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_request_session
from app.api.errors import ApiError
from app.api.schemas.evolution_steps import (
    DatasetInputSnapshotResponse,
    LinkedRunResponse,
    RunSnapshotResponse,
    RunSummaryResponse,
)
from app.api.schemas.runs import (
    BestStepMetricItemResponse,
    BestStepMetricsResponse,
    RunCandidatePageResponse,
    RunCandidateResponse,
    RunSyncResponse,
)
from app.config import load_settings
from app.infrastructure.database import transaction_scope
from app.infrastructure.mlflow_run_loader import MlflowRunLoader
from app.infrastructure.mlflow_run_search import MlflowRunSearch
from app.infrastructure.run_repository import RunRepository, RunSnapshotRecord
from app.services.best_step_metrics_service import BestStepMetricsService
from app.services.run_sync_service import RunSyncService

router = APIRouter(prefix="/runs", tags=["runs"])
SessionDependency = Annotated[Session, Depends(get_request_session)]


def get_mlflow_client() -> MlflowClient:
    """Build an MLflow client using the configured Tracking Server URI.

    Returns:
        MlflowClient: Client used only by the Run search and sync boundaries.
    """
    return MlflowClient(tracking_uri=load_settings().mlflow_tracking_uri)


MlflowClientDependency = Annotated[MlflowClient, Depends(get_mlflow_client)]


@router.get("", response_model=RunCandidatePageResponse)
def search_runs(
    query: str | None = Query(default=None, max_length=255),
    page_token: str | None = Query(default=None, alias="pageToken"),
    client: MlflowClientDependency = None,
) -> RunCandidatePageResponse:
    """Return one deterministic page of selectable active MLflow Runs.

    Args:
        query: Optional case-insensitive partial Run-name filter.
        page_token: Opaque token returned by the previous candidate page.
        client: MLflow client used for the candidate search.

    Returns:
        RunCandidatePageResponse: Candidate fields and optional continuation token.
    """
    try:
        page = MlflowRunSearch(client).search(query, page_token)
    except (KeyError, OSError, ValueError) as error:
        raise ApiError(502, "mlflow_unavailable", "MLflow Runs could not be searched.") from error
    return RunCandidatePageResponse(
        items=[
            RunCandidateResponse(
                run_id=item.run_id,
                run_name=item.run_name,
                mlflow_experiment_id=item.mlflow_experiment_id,
                mlflow_experiment_name=item.mlflow_experiment_name,
                status=item.status,
                started_at=item.started_at,
                ended_at=item.ended_at,
            )
            for item in page.items
        ],
        next_page_token=page.next_page_token,
    )


@router.post("/{runId}/sync", response_model=RunSyncResponse)
def sync_run(
    run_id: Annotated[str, Path(alias="runId", max_length=64, pattern=r"^\S+$")],
    session: SessionDependency,
    client: MlflowClientDependency,
) -> RunSyncResponse:
    """Synchronize a linked Run's mutable metadata and terminal Snapshot once.

    Args:
        run_id: MLflow Run identifier linked to an Evolution Step.
        session: Request-scoped local database Session.
        client: MLflow client used to read current Run data.

    Returns:
        RunSyncResponse: Updated local Reference and optional immutable Snapshot.
    """
    try:
        with transaction_scope(session):
            connection = session.connection()
            result = RunSyncService(connection, MlflowRunLoader(client)).sync(
                run_id,
                datetime.now(UTC).replace(tzinfo=None),
            )
            return RunSyncResponse(
                run=_linked_run_response(RunRepository(connection), result.reference.run_id),
            )
    except (KeyError, OSError) as error:
        raise ApiError(502, "mlflow_unavailable", "MLflow Run could not be loaded.") from error


@router.get("/{runId}/best-step-metrics", response_model=BestStepMetricsResponse)
def get_best_step_metrics(
    run_id: Annotated[str, Path(alias="runId", max_length=64, pattern=r"^\S+$")],
    session: SessionDependency,
) -> BestStepMetricsResponse:
    """Return canonical Metrics stored at one Run's best-accuracy step.

    Args:
        run_id: Locally linked Run identifier from the URL path.
        session: Request-scoped local database Session.

    Returns:
        BestStepMetricsResponse: Available local Metric items or reason state.
    """
    try:
        result = BestStepMetricsService(RunRepository(session.connection())).get(run_id)
    except LookupError as error:
        raise ApiError(404, "not_found", str(error)) from error
    return BestStepMetricsResponse(
        run_id=result.run_id,
        status=result.status,
        unavailable_reason=result.unavailable_reason,
        best_accuracy=result.best_accuracy,
        best_accuracy_step=result.best_accuracy_step,
        best_accuracy_recorded_at=result.best_accuracy_recorded_at,
        items=[
            BestStepMetricItemResponse(
                name=item.name,
                value=item.value,
                step=item.step,
                recorded_at=item.recorded_at,
            )
            for item in result.items
        ],
    )


def _linked_run_response(
    repository: RunRepository,
    run_id: str,
) -> LinkedRunResponse:
    """Map locally saved Run data to the synchronization response structure.

    Args:
        repository: Local persistence boundary used for saved Run reads.
        run_id: Reference identifier that was just synchronized.

    Returns:
        LinkedRunResponse: Current Reference and optional immutable Snapshot.
    """
    reference = repository.get_reference(run_id)
    if reference is None:
        raise LookupError(f"Run {run_id} was not found")
    snapshot = repository.get_snapshot(run_id)
    return LinkedRunResponse(
        reference=RunSummaryResponse(
            run_id=reference.run_id,
            mlflow_experiment_id=reference.mlflow_experiment_id,
            run_name=reference.run_name,
            current_status=reference.current_status,
            started_at=reference.started_at,
            ended_at=reference.ended_at,
            last_synced_at=reference.last_synced_at,
            snapshot_state="captured" if snapshot is not None else "pending",
            snapshot_captured_at=None if snapshot is None else snapshot.captured_at,
        ),
        snapshot=None if snapshot is None else _snapshot_response(snapshot),
    )


def _snapshot_response(snapshot: RunSnapshotRecord) -> RunSnapshotResponse:
    """Map a captured Snapshot to the synchronization response schema.

    Args:
        snapshot: Immutable terminal data read from the local database.

    Returns:
        RunSnapshotResponse: Captured Parameters and Dataset Inputs.
    """
    return RunSnapshotResponse(
        run_id=snapshot.run_id,
        status_at_capture=snapshot.status_at_capture,
        started_at=snapshot.started_at,
        ended_at=snapshot.ended_at,
        best_accuracy=snapshot.best_accuracy,
        best_accuracy_step=snapshot.best_accuracy_step,
        best_accuracy_recorded_at=snapshot.best_accuracy_recorded_at,
        captured_at=snapshot.captured_at,
        parameters=snapshot.parameters,
        datasets=[
            DatasetInputSnapshotResponse(
                ordinal=item.ordinal,
                name=item.name,
                digest=item.digest,
                source_type=item.source_type,
                source=item.source,
                schema_value=item.schema,
                profile=item.profile,
                context=item.context,
            )
            for item in snapshot.datasets
        ],
    )
