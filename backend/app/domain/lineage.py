"""Validation and traversal rules for current Run-link Lineage edges."""

from collections.abc import Iterable


class ResultRunConflictError(ValueError):
    """Signal that another Evolution Step already owns a result Run."""


class LineageCycleError(ValueError):
    """Signal that proposed current Run links would form a cycle."""


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
