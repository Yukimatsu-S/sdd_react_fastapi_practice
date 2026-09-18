"""Synchronous HTTP routes for Evolution Step create, read, and edit flows."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from mlflow import MlflowClient
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.api.dependencies import get_request_session
from app.api.errors import ApiError
from app.api.schemas.evolution_steps import (
    DatasetInputSnapshotResponse,
    EvolutionStepCreateRequest,
    EvolutionStepDetailResponse,
    EvolutionStepPatchRequest,
    HistoryEntryResponse,
    LinkedRunResponse,
    RunSnapshotResponse,
    RunSummaryResponse,
)
from app.config import load_settings
from app.domain.lineage import LineageCycleError, ResultRunConflictError
from app.infrastructure.database import transaction_scope
from app.infrastructure.evolution_step_repository import (
    EvolutionStepRecord,
    EvolutionStepRepository,
)
from app.infrastructure.mlflow_run_loader import MlflowRunLoader
from app.infrastructure.run_repository import RunRepository, RunSnapshotRecord
from app.services.evolution_step_service import EvolutionStepService

router = APIRouter(prefix="/evolution-steps", tags=["evolution-steps"])
SessionDependency = Annotated[Session, Depends(get_request_session)]


def get_run_loader() -> MlflowRunLoader:
    """Build the MLflow loader used only when a route needs selected Run data.

    Returns:
        MlflowRunLoader: Loader configured for the environment's Tracking Server.
    """
    settings = load_settings()
    return MlflowRunLoader(MlflowClient(tracking_uri=settings.mlflow_tracking_uri))


RunLoaderDependency = Annotated[MlflowRunLoader, Depends(get_run_loader)]


@router.post("", response_model=EvolutionStepDetailResponse, status_code=201)
def create_evolution_step(
    request: EvolutionStepCreateRequest,
    session: SessionDependency,
    run_loader: RunLoaderDependency,
) -> EvolutionStepDetailResponse:
    """Create one Evolution Step and immediately return its saved local detail.

    Args:
        request: Validated JSON create body.
        session: Request-scoped database Session.
        run_loader: MLflow loader for selected parent/result Runs.

    Returns:
        EvolutionStepDetailResponse: Newly saved Step with local linked Run state.
    """
    try:
        with transaction_scope(session):
            connection = session.connection()
            step = EvolutionStepService(connection, run_loader).create(
                purpose=request.purpose,
                hypothesis=request.hypothesis,
                change_description=request.change_description,
                parent_run_id=request.parent_run_id,
                result_run_id=request.result_run_id,
                now=datetime.now(UTC).replace(tzinfo=None),
            )
            return _detail_response(connection, step)
    except (ResultRunConflictError, LineageCycleError) as error:
        raise ApiError(409, "lineage_conflict", str(error)) from error
    except (KeyError, OSError) as error:
        raise ApiError(502, "mlflow_unavailable", "MLflow Run could not be loaded.") from error
    except ValueError as error:
        raise ApiError(422, "validation_error", str(error)) from error


@router.get("/{evolutionStepId}", response_model=EvolutionStepDetailResponse)
def get_evolution_step(
    evolution_step_id: Annotated[int, Path(alias="evolutionStepId", ge=1)],
    session: SessionDependency,
) -> EvolutionStepDetailResponse:
    """Return one saved Evolution Step without synchronizing MLflow data.

    Args:
        evolution_step_id: Positive Step identifier from the URL path.
        session: Request-scoped database Session.

    Returns:
        EvolutionStepDetailResponse: Stored detail and local linked Run state.
    """
    try:
        connection = session.connection()
        step = EvolutionStepRepository(connection).get(evolution_step_id)
        return _detail_response(connection, step)
    except LookupError as error:
        raise ApiError(404, "not_found", str(error)) from error


@router.patch("/{evolutionStepId}", response_model=EvolutionStepDetailResponse)
def patch_evolution_step(
    request: EvolutionStepPatchRequest,
    evolution_step_id: Annotated[int, Path(alias="evolutionStepId", ge=1)],
    session: SessionDependency,
    run_loader: RunLoaderDependency,
) -> EvolutionStepDetailResponse:
    """Apply a partial Evolution Step update and return freshly saved detail.

    Args:
        request: Validated partial JSON body including explicit null unlinks.
        evolution_step_id: Positive Step identifier from the URL path.
        session: Request-scoped database Session.
        run_loader: MLflow loader for newly selected Runs.

    Returns:
        EvolutionStepDetailResponse: Detail after the successful update.
    """
    try:
        with transaction_scope(session):
            connection = session.connection()
            step = EvolutionStepService(connection, run_loader).patch(
                evolution_step_id,
                request.supplied_changes(),
                datetime.now(UTC).replace(tzinfo=None),
            )
            return _detail_response(connection, step)
    except LookupError as error:
        raise ApiError(404, "not_found", str(error)) from error
    except (ResultRunConflictError, LineageCycleError) as error:
        raise ApiError(409, "lineage_conflict", str(error)) from error
    except (KeyError, OSError) as error:
        raise ApiError(502, "mlflow_unavailable", "MLflow Run could not be loaded.") from error
    except ValueError as error:
        raise ApiError(422, "validation_error", str(error)) from error


def _detail_response(
    connection: Connection,
    step: EvolutionStepRecord,
) -> EvolutionStepDetailResponse:
    """Map stored Step and Run repository records to the HTTP detail schema.

    Args:
        connection: Connection used for local read-only repository queries.
        step: Current Evolution Step record already read or mutated by the service.

    Returns:
        EvolutionStepDetailResponse: CamelCase-ready local detail response.
    """
    step_repository = EvolutionStepRepository(connection)
    run_repository = RunRepository(connection)
    return EvolutionStepDetailResponse(
        id=step.id,
        purpose=step.purpose,
        hypothesis=step.hypothesis,
        change_description=step.change_description,
        parent_run=_linked_run_response(run_repository, step.parent_run_id),
        result_run=_linked_run_response(run_repository, step.result_run_id),
        history=[
            HistoryEntryResponse(
                field=entry.field,
                old_value=entry.old_value,
                new_value=entry.new_value,
                changed_at=entry.changed_at,
            )
            for entry in step_repository.history(step.id)
        ],
        created_at=step.created_at,
        updated_at=step.updated_at,
    )


def _linked_run_response(
    repository: RunRepository,
    run_id: str | None,
) -> LinkedRunResponse | None:
    """Map an optional linked Run ID to local Reference and Snapshot response data.

    Args:
        repository: Local Run Reference and Snapshot persistence boundary.
        run_id: Optional Run ID linked to the current Evolution Step.

    Returns:
        LinkedRunResponse | None: Local Run state, or no linked Run.
    """
    if run_id is None:
        return None
    reference = repository.get_reference(run_id)
    if reference is None:
        return None
    snapshot = repository.get_snapshot(run_id)
    return LinkedRunResponse(
        reference=RunSummaryResponse(
            run_id=reference.run_id,
            mlflow_experiment_id=reference.mlflow_experiment_id,
            run_name=reference.run_name,
            status=reference.current_status,
            started_at=reference.started_at,
            ended_at=reference.ended_at,
            last_synced_at=reference.last_synced_at,
            snapshot_state="captured" if snapshot is not None else "pending",
            snapshot_captured_at=None if snapshot is None else snapshot.captured_at,
        ),
        snapshot=None if snapshot is None else _snapshot_response(snapshot),
    )


def _snapshot_response(snapshot: RunSnapshotRecord) -> RunSnapshotResponse:
    """Map immutable persisted Snapshot data to its HTTP response schema.

    Args:
        snapshot: Snapshot read from local immutable storage.

    Returns:
        RunSnapshotResponse: Serialized Parameters and Dataset Inputs.
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
