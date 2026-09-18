"""Specify compact list-summary availability states before list persistence exists."""

from app.domain.comparison import build_comparison_summary


def test_available_summary_has_null_reasons_and_counts_changes() -> None:
    """Keep available states distinct from unavailable states and reasons."""
    summary = build_comparison_summary(
        parent_snapshot={"parameters": {"epoch": "10"}, "best_accuracy": 0.90, "datasets": []},
        result_snapshot={"parameters": {"epoch": "20"}, "best_accuracy": 0.92, "datasets": []},
    )

    assert summary.status == "available"
    assert summary.unavailable_reason is None
    assert summary.parameter_change_count == 1
    assert summary.accuracy.delta == 0.02
    assert summary.dataset_status == "unchanged"
    assert summary.dataset_unavailable_reason is None


def test_missing_snapshot_has_explicit_unavailable_reasons() -> None:
    """Never represent missing Snapshot data as an unchanged comparison."""
    summary = build_comparison_summary(parent_snapshot=None, result_snapshot=None)

    assert summary.status == "unavailable"
    assert summary.unavailable_reason == "snapshot_pending"
    assert summary.parameter_change_count is None
    assert summary.accuracy.status == "unavailable"
    assert summary.dataset_status == "unavailable"
    assert summary.dataset_unavailable_reason == "comparison_unavailable"
