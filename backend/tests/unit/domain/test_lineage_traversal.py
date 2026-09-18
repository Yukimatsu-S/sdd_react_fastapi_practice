"""Specify deterministic traversal over current Evolution Step Run links."""

from app.domain.lineage import LineageEdge, traverse_ancestors, traverse_descendants


EDGES = (
    LineageEdge(1, "external-root", "run-1"),
    LineageEdge(2, "run-1", "run-2"),
    LineageEdge(3, "run-2", "run-3"),
    LineageEdge(4, "run-2", "run-4"),
    LineageEdge(5, "run-3", "run-5"),
)


def test_ancestors_are_nearest_first_and_stop_at_upstream_boundary() -> None:
    """Trace result ownership backwards without inventing an external Step."""
    ancestors = traverse_ancestors(selected_step_id=2, edges=EDGES)

    assert [(item.evolution_step_id, item.distance_from_selected) for item in ancestors] == [(1, 1)]
    assert ancestors[0].parent_evolution_step_id is None


def test_descendants_use_breadth_first_distance_then_step_id_order() -> None:
    """Keep shared-parent branches visible in stable generation order."""
    descendants = traverse_descendants(selected_step_id=2, edges=EDGES)

    assert [
        (item.evolution_step_id, item.distance_from_selected, item.parent_evolution_step_id)
        for item in descendants
    ] == [
        (3, 1, 2),
        (4, 1, 2),
        (5, 2, 3),
    ]


def test_missing_parent_run_has_no_ancestor_or_upstream_boundary_step() -> None:
    """Treat a Step without a parent Run as the root of its visible lineage."""
    root = LineageEdge(10, None, "run-10")

    assert traverse_ancestors(selected_step_id=10, edges=(root,)) == ()
