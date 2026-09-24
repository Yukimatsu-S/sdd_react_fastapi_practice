"""Selected-centered reads over current Evolution Step Run links."""

from dataclasses import dataclass

from sqlalchemy.engine import Connection

from app.domain.lineage import (
    LineageEdge,
    TraversedLineageStep,
    traverse_ancestors,
    traverse_descendants,
)
from app.infrastructure.evolution_step_repository import (
    EvolutionStepRecord,
    EvolutionStepRepository,
)
from app.infrastructure.run_repository import RunReferenceRecord, RunRepository


@dataclass(frozen=True)
class LineageStep:
    """One current Evolution Step displayed at a position in a Lineage graph."""

    evolution_step: EvolutionStepRecord
    parent_evolution_step_id: int | None
    distance_from_selected: int
    parent_run: RunReferenceRecord | None
    result_run: RunReferenceRecord | None


@dataclass(frozen=True)
class Lineage:
    """One selected Step together with its ordered current ancestors and descendants."""

    selected: LineageStep
    ancestors: tuple[LineageStep, ...]
    descendants: tuple[LineageStep, ...]


class LineageService:
    """Assemble one current-link Lineage without reading historical links or MLflow."""

    def __init__(self, connection: Connection) -> None:
        """Create local repositories that share the caller-owned connection.

        Args:
            connection: Open connection used only for local Lineage reads.
        """
        self._steps = EvolutionStepRepository(connection)
        self._runs = RunRepository(connection)

    def get(self, evolution_step_id: int) -> Lineage:
        """Return the current Lineage centered on one saved Evolution Step.

        Args:
            evolution_step_id: Positive local Step identifier selected by the user.

        Returns:
            Lineage: Selected Step with nearest-first ancestors and breadth-first descendants.

        Raises:
            LookupError: If the selected Step does not exist.
        """
        selected_record = self._steps.get(evolution_step_id)
        edges = self._steps.current_lineage_edges()
        edge_by_id = {edge.evolution_step_id: edge for edge in edges}
        selected_edge = edge_by_id[evolution_step_id]
        producer_by_result = _producer_by_result(edges)

        selected = self._to_lineage_step(
            selected_record,
            parent_evolution_step_id=_parent_step_id(selected_edge, producer_by_result),
            distance_from_selected=0,
        )
        ancestors = tuple(
            self._to_traversed_step(item)
            for item in traverse_ancestors(evolution_step_id, edges)
        )
        descendants = tuple(
            self._to_traversed_step(item)
            for item in traverse_descendants(evolution_step_id, edges)
        )
        return Lineage(selected=selected, ancestors=ancestors, descendants=descendants)

    def _to_traversed_step(self, traversed: TraversedLineageStep) -> LineageStep:
        """Load one graph position's saved Step and current Run references.

        Args:
            traversed: Pure traversal position derived from current Run links.

        Returns:
            LineageStep: Saved Step text, graph position, and current Run metadata.
        """
        return self._to_lineage_step(
            self._steps.get(traversed.evolution_step_id),
            parent_evolution_step_id=traversed.parent_evolution_step_id,
            distance_from_selected=traversed.distance_from_selected,
        )

    def _to_lineage_step(
        self,
        record: EvolutionStepRecord,
        *,
        parent_evolution_step_id: int | None,
        distance_from_selected: int,
    ) -> LineageStep:
        """Combine one saved Step with mutable reference displays.

        Args:
            record: Current persisted Step fields.
            parent_evolution_step_id: Local producer of the parent Run, if registered.
            distance_from_selected: Number of current links from the selected Step.

        Returns:
            LineageStep: One graph item ready for an API response mapping.
        """
        return LineageStep(
            evolution_step=record,
            parent_evolution_step_id=parent_evolution_step_id,
            distance_from_selected=distance_from_selected,
            parent_run=self._runs.get_reference(record.parent_run_id)
            if record.parent_run_id is not None
            else None,
            result_run=self._runs.get_reference(record.result_run_id)
            if record.result_run_id is not None
            else None,
        )


def _producer_by_result(edges: tuple[LineageEdge, ...]) -> dict[str, LineageEdge]:
    """Index the one current Step that produces each linked result Run.

    Args:
        edges: All current Evolution Step Run links.

    Returns:
        dict[str, LineageEdge]: Result Run ID to its owning current Step link.
    """
    return {
        edge.result_run_id: edge
        for edge in edges
        if edge.result_run_id is not None
    }


def _parent_step_id(
    edge: LineageEdge,
    producer_by_result: dict[str, LineageEdge],
) -> int | None:
    """Find the local Step that produced one current parent Run.

    Args:
        edge: Current link whose parent Run is being resolved.
        producer_by_result: Current result Run ownership index.

    Returns:
        int | None: Producing Step ID, or ``None`` for a root or external boundary.
    """
    if edge.parent_run_id is None:
        return None
    parent = producer_by_result.get(edge.parent_run_id)
    return None if parent is None else parent.evolution_step_id
