"""Compact immutable-Snapshot comparison summaries used by Evolution Step lists."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AccuracySummary:
    """Available best-accuracy values or a precise unavailable reason."""

    status: str
    unavailable_reason: str | None
    parent_best: float | None
    result_best: float | None
    delta: float | None


@dataclass(frozen=True)
class ComparisonSummary:
    """Small list-safe summary of two finalized Run Snapshots."""

    status: str
    unavailable_reason: str | None
    parameter_change_count: int | None
    accuracy: AccuracySummary
    dataset_status: str
    dataset_unavailable_reason: str | None


def build_comparison_summary(
    parent_snapshot: dict[str, Any] | None,
    result_snapshot: dict[str, Any] | None,
) -> ComparisonSummary:
    """Build one compact comparison without reading mutable Run Reference fields.

    Args:
        parent_snapshot: Immutable parent Snapshot values, if captured.
        result_snapshot: Immutable result Snapshot values, if captured.

    Returns:
        Available summary or explicit reasons when either Snapshot is absent.
    """
    if parent_snapshot is None or result_snapshot is None:
        unavailable_accuracy = AccuracySummary(
            status="unavailable",
            unavailable_reason="comparison_unavailable",
            parent_best=None,
            result_best=None,
            delta=None,
        )
        return ComparisonSummary(
            status="unavailable",
            unavailable_reason="snapshot_pending",
            parameter_change_count=None,
            accuracy=unavailable_accuracy,
            dataset_status="unavailable",
            dataset_unavailable_reason="comparison_unavailable",
        )

    parent_parameters = parent_snapshot.get("parameters", {})
    result_parameters = result_snapshot.get("parameters", {})
    changed_parameter_count = sum(
        parent_parameters.get(name) != result_parameters.get(name)
        for name in set(parent_parameters) | set(result_parameters)
    )
    parent_accuracy = parent_snapshot.get("best_accuracy")
    result_accuracy = result_snapshot.get("best_accuracy")
    accuracy = _accuracy_summary(parent_accuracy, result_accuracy)
    dataset_status = (
        "unchanged" if parent_snapshot.get("datasets", []) == result_snapshot.get("datasets", []) else "changed"
    )
    return ComparisonSummary(
        status="available",
        unavailable_reason=None,
        parameter_change_count=changed_parameter_count,
        accuracy=accuracy,
        dataset_status=dataset_status,
        dataset_unavailable_reason=None,
    )


def _accuracy_summary(parent_best: float | None, result_best: float | None) -> AccuracySummary:
    """Return accuracy values only when both finalized Snapshots provide them.

    Args:
        parent_best: Parent Snapshot best accuracy.
        result_best: Result Snapshot best accuracy.

    Returns:
        Available values and delta, or the accuracy-specific unavailable state.
    """
    if parent_best is None or result_best is None:
        return AccuracySummary("unavailable", "accuracy_missing", None, None, None)
    return AccuracySummary("available", None, parent_best, result_best, round(result_best - parent_best, 12))
