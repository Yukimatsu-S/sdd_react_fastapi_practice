"""Validation and traversal rules for current Run-link Lineage edges."""

from collections.abc import Iterable
from dataclasses import dataclass


class ResultRunConflictError(ValueError):
    """Signal that another Evolution Step already owns a result Run."""


class LineageCycleError(ValueError):
    """Signal that proposed current Run links would form a cycle."""


@dataclass(frozen=True)
class LineageEdge:
    """Current parent-to-result Run link for one Evolution Step."""

    evolution_step_id: int
    parent_run_id: str | None
    result_run_id: str | None


@dataclass(frozen=True)
class TraversedLineageStep:
    """One Step reached from a selected Step by current-link traversal."""

    evolution_step_id: int
    parent_evolution_step_id: int | None
    distance_from_selected: int


def validate_distinct_run_links(parent_run_id: str | None, result_run_id: str | None) -> None:
    """Reject a proposed Evolution Step edge from a Run to itself.

    Args:
        parent_run_id: Optional Run used as the improvement source.
        result_run_id: Optional Run produced by the improvement.

    Raises:
        ValueError: If both supplied Run IDs are the same.
    """
    if parent_run_id is not None and parent_run_id == result_run_id:
        raise ValueError("parent and result Run IDs must not be the same")


def validate_result_run_is_available(result_run_id: str | None, claimed_run_ids: set[str]) -> None:
    """Reject a result Run that is already owned by another Evolution Step.

    Args:
        result_run_id: Optional proposed result Run ID.
        claimed_run_ids: Result Run IDs currently owned by other Steps.

    Raises:
        ResultRunConflictError: If the proposed result Run is already claimed.
    """
    if result_run_id is not None and result_run_id in claimed_run_ids:
        raise ResultRunConflictError(f"result Run {result_run_id} is already linked")


def validate_lineage_is_acyclic(edges: Iterable[tuple[str, str]]) -> None:
    """Reject current parent-to-result edges that form a directed Run cycle.

    Args:
        edges: Complete current `(parent_run_id, result_run_id)` Run edges.

    Raises:
        LineageCycleError: If depth-first traversal reaches a Run being visited.
    """
    children_by_parent: dict[str, set[str]] = {}
    for parent_run_id, result_run_id in edges:
        children_by_parent.setdefault(parent_run_id, set()).add(result_run_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(run_id: str) -> None:
        """Traverse one Run and its result Runs in deterministic order.

        Args:
            run_id: Current Run reached by the depth-first traversal.

        Raises:
            LineageCycleError: If this Run is already on the traversal path.
        """
        if run_id in visiting:
            raise LineageCycleError("proposed Run links create a cycle")
        if run_id in visited:
            return

        visiting.add(run_id)
        for child_run_id in sorted(children_by_parent.get(run_id, ())):
            visit(child_run_id)
        visiting.remove(run_id)
        visited.add(run_id)

    for run_id in sorted(children_by_parent):
        visit(run_id)


def traverse_ancestors(
    selected_step_id: int,
    edges: Iterable[LineageEdge],
) -> tuple[TraversedLineageStep, ...]:
    """Return ancestors nearest-first from current result-to-parent ownership.

    Args:
        selected_step_id: Step at the center of the requested Lineage.
        edges: All current Evolution Step links.

    Returns:
        tuple[TraversedLineageStep, ...]: Nearest-to-farthest ancestor Steps.
    """
    edges_by_id = {edge.evolution_step_id: edge for edge in edges}
    selected = edges_by_id[selected_step_id]
    producer_by_result = {
        edge.result_run_id: edge
        for edge in edges_by_id.values()
        if edge.result_run_id is not None
    }
    ancestors: list[TraversedLineageStep] = []
    current = selected
    distance = 1
    while current.parent_run_id is not None:
        ancestor = producer_by_result.get(current.parent_run_id)
        if ancestor is None:
            break
        parent_producer = producer_by_result.get(ancestor.parent_run_id)
        ancestors.append(
            TraversedLineageStep(
                ancestor.evolution_step_id,
                None if parent_producer is None else parent_producer.evolution_step_id,
                distance,
            ),
        )
        current = ancestor
        distance += 1
    return tuple(ancestors)


def traverse_descendants(
    selected_step_id: int,
    edges: Iterable[LineageEdge],
) -> tuple[TraversedLineageStep, ...]:
    """Return descendants breadth-first, ordered by distance then Step ID.

    Args:
        selected_step_id: Step at the center of the requested Lineage.
        edges: All current Evolution Step links.

    Returns:
        tuple[TraversedLineageStep, ...]: Stable descendant Steps with direct parent IDs.
    """
    edges_by_id = {edge.evolution_step_id: edge for edge in edges}
    children_by_parent: dict[str, list[LineageEdge]] = {}
    for edge in edges_by_id.values():
        if edge.parent_run_id is not None:
            children_by_parent.setdefault(edge.parent_run_id, []).append(edge)

    selected = edges_by_id[selected_step_id]
    queue: list[tuple[LineageEdge, int]] = [(selected, 0)]
    descendants: list[TraversedLineageStep] = []
    while queue:
        parent, distance = queue.pop(0)
        if parent.result_run_id is None:
            continue
        children = sorted(children_by_parent.get(parent.result_run_id, []), key=lambda edge: edge.evolution_step_id)
        for child in children:
            descendants.append(
                TraversedLineageStep(child.evolution_step_id, parent.evolution_step_id, distance + 1),
            )
            queue.append((child, distance + 1))
    return tuple(descendants)
