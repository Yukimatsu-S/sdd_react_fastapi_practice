"""Create Evolution Steps as one transaction-owned application use case."""

from datetime import datetime

from sqlalchemy.engine import Connection

from app.domain.evolution_step import (
    validate_change_description,
    validate_required_text,
)
from app.domain.lineage import (
    validate_distinct_run_links,
    validate_lineage_is_acyclic,
    validate_result_run_is_available,
)
from app.infrastructure.evolution_step_repository import (
    EvolutionStepRecord,
    EvolutionStepRepository,
)
from app.infrastructure.mlflow_gateway import LoadedRun, RunLoaderGateway
from app.infrastructure.run_repository import RunReferenceRecord, RunRepository


class EvolutionStepService:
    """Coordinate selected-Run validation and atomic Evolution Step creation."""

    def __init__(self, connection: Connection, run_loader: RunLoaderGateway) -> None:
        """Store the database connection and MLflow loader for one use case.

        Args:
            connection: Connection used for the complete create transaction.
            run_loader: Gateway used to verify and load selected Run references.
        """
        self._connection = connection
        self._run_loader = run_loader

    def create(
        self,
        *,
        purpose: str,
        hypothesis: str,
        change_description: str | None,
        parent_run_id: str | None,
        result_run_id: str | None,
        now: datetime,
    ) -> EvolutionStepRecord:
        """Create one Step after validating and saving its selected Run references.

        Args:
            purpose: Required intent of the proposed improvement.
            hypothesis: Required expected outcome.
            change_description: Optional description of planned changes.
            parent_run_id: Optional source Run identifier.
            result_run_id: Optional produced Run identifier.
            now: UTC timestamp supplied by the request boundary.

        Returns:
            EvolutionStepRecord: Newly persisted Step without initial history rows.

        Raises:
            ValueError: If submitted text or Run links violate a domain rule.
        """
        validate_required_text(purpose, "purpose")
        validate_required_text(hypothesis, "hypothesis")
        validate_change_description(change_description)
        validate_distinct_run_links(parent_run_id, result_run_id)

        with self._connection.begin():
            step_repository = EvolutionStepRepository(self._connection)
            run_repository = RunRepository(self._connection)
            step_repository.lock_lineage_mutation_guard()

            for loaded_run in self._load_selected_runs(parent_run_id, result_run_id):
                run_repository.upsert_reference(_to_reference_record(loaded_run, now))

            validate_result_run_is_available(
                result_run_id,
                step_repository.claimed_result_run_ids(),
            )
            edges = list(step_repository.current_edges())
            if parent_run_id is not None and result_run_id is not None:
                edges.append((parent_run_id, result_run_id))
            validate_lineage_is_acyclic(edges)
            return step_repository.create(
                purpose=purpose,
                hypothesis=hypothesis,
                change_description=change_description,
                parent_run_id=parent_run_id,
                result_run_id=result_run_id,
                now=now,
            )

    def _load_selected_runs(
        self,
        parent_run_id: str | None,
        result_run_id: str | None,
    ) -> tuple[LoadedRun, ...]:
        """Load each non-null selected Run once before persisting its reference.

        Args:
            parent_run_id: Optional selected parent Run.
            result_run_id: Optional selected result Run.

        Returns:
            tuple[LoadedRun, ...]: Loaded Runs in parent then result order.
        """
        run_ids = tuple(run_id for run_id in (parent_run_id, result_run_id) if run_id is not None)
        return tuple(self._run_loader.load(run_id) for run_id in run_ids)


def _to_reference_record(loaded_run: LoadedRun, synced_at: datetime) -> RunReferenceRecord:
    """Map MLflow-derived current metadata to the repository record.

    Args:
        loaded_run: Current Run data read through the MLflow gateway.
        synced_at: UTC timestamp at which the gateway read completed.

    Returns:
        RunReferenceRecord: Mutable metadata ready for database persistence.
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
