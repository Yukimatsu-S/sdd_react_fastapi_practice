"""Specify Run-link ownership and current Lineage cycle rules."""

import pytest

from app.domain.lineage import (
    LineageCycleError,
    ResultRunConflictError,
    validate_distinct_run_links,
    validate_lineage_is_acyclic,
    validate_result_run_is_available,
)


def test_result_run_cannot_be_owned_by_two_evolution_steps() -> None:
    """Reject a result Run already claimed by another Evolution Step."""
    with pytest.raises(ResultRunConflictError, match="run-result"):
        validate_result_run_is_available("run-result", {"run-result"})


def test_parent_and_result_cannot_be_the_same_run() -> None:
    """Reject a self-edge before creating a Lineage graph."""
    with pytest.raises(ValueError, match="same"):
        validate_distinct_run_links("run-001", "run-001")


def test_multi_generation_run_cycle_is_rejected() -> None:
    """Reject a back-edge that closes a three-generation Run cycle."""
    edges = (
        ("run-001", "run-002"),
        ("run-002", "run-003"),
        ("run-003", "run-001"),
    )

    with pytest.raises(LineageCycleError, match="cycle"):
        validate_lineage_is_acyclic(edges)


def test_lineage_allows_multiple_children_for_one_parent_run() -> None:
    """Permit the fan-out that represents separate later improvements."""
    edges = (
        ("run-001", "run-002"),
        ("run-001", "run-003"),
        ("run-003", "run-004"),
    )

    validate_lineage_is_acyclic(edges)
