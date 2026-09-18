"""Specify comparison availability and unavailable-reason precedence."""

from app.services.comparison_service import assemble_comparison


def _snapshot(best_accuracy: float | None = 0.9) -> dict[str, object]:
    """Create the smallest finalized Snapshot value set for availability tests.

    Args:
        best_accuracy: Captured best accuracy, or ``None`` when it was not recorded.

    Returns:
        dict[str, object]: Immutable fields used by comparison assembly.
    """
    return {"parameters": {}, "best_accuracy": best_accuracy, "datasets": ()}


def test_comparison_uses_the_documented_missing_run_precedence() -> None:
    """Report a missing parent before every later unavailable prerequisite."""
    comparison = assemble_comparison(
        parent_run_id=None,
        parent_snapshot=None,
        result_run_id=None,
        result_snapshot=None,
    )

    assert comparison.status == "unavailable"
    assert comparison.unavailable_reason == "parent_run_missing"
    assert comparison.parameters == ()
    assert comparison.accuracy.unavailable_reason == "comparison_unavailable"
    assert comparison.datasets.unavailable_reason == "comparison_unavailable"


def test_comparison_reports_pending_snapshots_in_parent_then_result_order() -> None:
    """Keep Snapshot-pending reasons deterministic when both links exist."""
    parent_pending = assemble_comparison(
        parent_run_id="run-parent",
        parent_snapshot=None,
        result_run_id="run-result",
        result_snapshot=None,
    )
    result_pending = assemble_comparison(
        parent_run_id="run-parent",
        parent_snapshot=_snapshot(),
        result_run_id="run-result",
        result_snapshot=None,
    )

    assert parent_pending.unavailable_reason == "parent_snapshot_pending"
    assert result_pending.unavailable_reason == "result_snapshot_pending"


def test_available_comparison_keeps_section_unavailability_independent() -> None:
    """Allow Parameter comparison when only accuracy or Dataset inputs are missing."""
    comparison = assemble_comparison(
        parent_run_id="run-parent",
        parent_snapshot={"parameters": {"epochs": "10"}, "best_accuracy": None, "datasets": ()},
        result_run_id="run-result",
        result_snapshot={"parameters": {"epochs": "20"}, "best_accuracy": 0.92, "datasets": ()},
    )

    assert comparison.status == "available"
    assert comparison.unavailable_reason is None
    assert [(item.name, item.status) for item in comparison.parameters] == [("epochs", "changed")]
    assert comparison.accuracy.status == "unavailable"
    assert comparison.accuracy.unavailable_reason == "parent_accuracy_missing"
    assert comparison.datasets.status == "unavailable"
    assert comparison.datasets.unavailable_reason == "both_dataset_inputs_missing"
