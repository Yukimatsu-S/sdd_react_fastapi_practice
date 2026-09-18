"""SQLAlchemy Core persistence for Evolution Steps and their change history."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select, update
from sqlalchemy.engine import Connection

from app.domain.pagination import decode_cursor, encode_cursor
from app.infrastructure.models import (
    evolution_step,
    evolution_step_history,
    lineage_mutation_guard,
)

EDITABLE_FIELDS = {
    "purpose",
    "hypothesis",
    "change_description",
    "parent_run_id",
    "result_run_id",
}


@dataclass(frozen=True)
class EvolutionStepRecord:
    """Current persisted fields for one Evolution Step."""

    id: int
    purpose: str
    hypothesis: str
    change_description: str | None
    parent_run_id: str | None
    result_run_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class EvolutionStepHistoryRecord:
    """One append-only field change recorded after Step creation."""

    field: str
    old_value: str | None
    new_value: str | None
    changed_at: datetime


@dataclass(frozen=True)
class EvolutionStepPage:
    """One bounded page of current Evolution Steps and an opaque continuation."""

    items: tuple[EvolutionStepRecord, ...]
    next_page_token: str | None


class EvolutionStepRepository:
    """Persist current Step links and append only actual field changes."""

    def __init__(self, connection: Connection) -> None:
        """Store the transaction-owned connection used for all operations.

        Args:
            connection: Open SQLAlchemy connection owned by the caller's transaction.
        """
        self._connection = connection

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
        """Insert one Evolution Step without adding initial history rows.

        Args:
            purpose: Required improvement purpose.
            hypothesis: Required expected outcome.
            change_description: Optional manual change explanation.
            parent_run_id: Optional source Run ID.
            result_run_id: Optional produced Run ID.
            now: Caller-supplied UTC timestamp for creation and update fields.

        Returns:
            EvolutionStepRecord: Newly inserted current Step data.
        """
        result = self._connection.execute(
            evolution_step.insert().values(
                purpose=purpose,
                hypothesis=hypothesis,
                change_description=change_description,
                parent_run_id=parent_run_id,
                result_run_id=result_run_id,
                created_at=now,
                updated_at=now,
            ),
        )
        return self.get(int(result.inserted_primary_key[0]))

    def get(self, evolution_step_id: int) -> EvolutionStepRecord:
        """Return one persisted Evolution Step by identifier.

        Args:
            evolution_step_id: Primary key of the requested Step.

        Returns:
            EvolutionStepRecord: Current Step data.

        Raises:
            LookupError: If no Step has the requested identifier.
        """
        row = self._connection.execute(
            select(evolution_step).where(evolution_step.c.id == evolution_step_id),
        ).mappings().one_or_none()
        if row is None:
            raise LookupError(f"Evolution Step {evolution_step_id} was not found")
        return _to_step_record(row)

    def update(
        self,
        evolution_step_id: int,
        changes: Mapping[str, str | None],
        changed_at: datetime,
    ) -> EvolutionStepRecord:
        """Apply actual editable changes and append matching history rows.

        Args:
            evolution_step_id: Primary key of the Step to update.
            changes: Supplied field values; omitted fields remain unchanged.
            changed_at: Caller-supplied UTC timestamp for rows and history.

        Returns:
            EvolutionStepRecord: Current Step data after the update or no-op.

        Raises:
            ValueError: If changes include a field not tracked by this repository.
        """
        unknown_fields = set(changes).difference(EDITABLE_FIELDS)
        if unknown_fields:
            raise ValueError(f"unsupported Evolution Step fields: {sorted(unknown_fields)}")

        current = self.get(evolution_step_id)
        actual_changes = {
            field: value
            for field, value in changes.items()
            if getattr(current, field) != value
        }
        if not actual_changes:
            return current

        self._connection.execute(
            update(evolution_step)
            .where(evolution_step.c.id == evolution_step_id)
            .values(**actual_changes, updated_at=changed_at),
        )
        self._connection.execute(
            evolution_step_history.insert(),
            [
                {
                    "evolution_step_id": evolution_step_id,
                    "field": field,
                    "old_value": getattr(current, field),
                    "new_value": value,
                    "changed_at": changed_at,
                }
                for field, value in actual_changes.items()
            ],
        )
        return self.get(evolution_step_id)

    def history(self, evolution_step_id: int) -> tuple[EvolutionStepHistoryRecord, ...]:
        """Return append-only history in timestamp then internal-ID order.

        Args:
            evolution_step_id: Primary key of the Step whose history is requested.

        Returns:
            tuple[EvolutionStepHistoryRecord, ...]: Stable oldest-to-newest history.
        """
        rows = self._connection.execute(
            select(evolution_step_history)
            .where(evolution_step_history.c.evolution_step_id == evolution_step_id)
            .order_by(evolution_step_history.c.changed_at.asc(), evolution_step_history.c.id.asc()),
        ).mappings()
        return tuple(
            EvolutionStepHistoryRecord(
                field=str(row["field"]),
                old_value=row["old_value"],
                new_value=row["new_value"],
                changed_at=row["changed_at"],
            )
            for row in rows
        )

    def lock_lineage_mutation_guard(self) -> None:
        """Lock the singleton guard before any graph-wide Run-link mutation.

        Raises:
            LookupError: If the initial migration's required guard row is absent.
        """
        guard = self._connection.execute(
            select(lineage_mutation_guard.c.id)
            .where(lineage_mutation_guard.c.id == 1)
            .with_for_update(),
        ).scalar_one_or_none()
        if guard is None:
            raise LookupError("lineage mutation guard is missing")

    def current_edges(
        self,
        excluding_step_id: int | None = None,
    ) -> tuple[tuple[str, str], ...]:
        """Return complete current parent-to-result Run edges for cycle validation.

        Returns:
            tuple[tuple[str, str], ...]: Current non-null Run edges ordered by Step ID.
        """
        statement = (
            select(evolution_step.c.parent_run_id, evolution_step.c.result_run_id)
            .where(
                evolution_step.c.parent_run_id.is_not(None),
                evolution_step.c.result_run_id.is_not(None),
            )
            .order_by(evolution_step.c.id.asc())
        )
        if excluding_step_id is not None:
            statement = statement.where(evolution_step.c.id != excluding_step_id)
        rows = self._connection.execute(statement)
        return tuple((str(parent), str(result)) for parent, result in rows)

    def claimed_result_run_ids(self, excluding_step_id: int | None = None) -> set[str]:
        """Return every Run currently used as an Evolution Step result.

        Returns:
            set[str]: Result Run identifiers currently owned by any Step.
        """
        statement = select(evolution_step.c.result_run_id).where(
            evolution_step.c.result_run_id.is_not(None),
        )
        if excluding_step_id is not None:
            statement = statement.where(evolution_step.c.id != excluding_step_id)
        return set(self._connection.scalars(statement))

    def list_page(self, page_token: str | None) -> EvolutionStepPage:
        """Read at most twenty Steps in stable creation-time and ID descending order.

        Args:
            page_token: Opaque boundary from the preceding response, if any.

        Returns:
            Twenty current Steps at most and a token only when another row exists.

        Raises:
            ValueError: If the supplied token cannot be decoded.
        """
        statement = select(evolution_step).order_by(
            evolution_step.c.created_at.desc(),
            evolution_step.c.id.desc(),
        )
        if page_token is not None:
            cursor_created_at, cursor_id = decode_cursor(page_token)
            naive_cursor_time = cursor_created_at.astimezone(UTC).replace(tzinfo=None)
            statement = statement.where(
                or_(
                    evolution_step.c.created_at < naive_cursor_time,
                    and_(
                        evolution_step.c.created_at == naive_cursor_time,
                        evolution_step.c.id < cursor_id,
                    ),
                ),
            )

        rows = self._connection.execute(statement.limit(21)).mappings().all()
        records = tuple(_to_step_record(row) for row in rows[:20])
        next_page_token = None
        if len(rows) == 21:
            boundary = records[-1]
            next_page_token = encode_cursor(boundary.created_at.replace(tzinfo=UTC), boundary.id)
        return EvolutionStepPage(items=records, next_page_token=next_page_token)


def _to_step_record(row: Mapping[str, object]) -> EvolutionStepRecord:
    """Convert one SQLAlchemy mapping row into the repository's typed record.

    Args:
        row: Row mapping selected from the Evolution Step table.

    Returns:
        EvolutionStepRecord: Typed current Step representation.
    """
    return EvolutionStepRecord(
        id=int(row["id"]),
        purpose=str(row["purpose"]),
        hypothesis=str(row["hypothesis"]),
        change_description=row["change_description"],
        parent_run_id=row["parent_run_id"],
        result_run_id=row["result_run_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
