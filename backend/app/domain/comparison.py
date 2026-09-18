"""Shared complete and compact comparison rules for immutable Run Snapshots."""

from dataclasses import dataclass
from typing import Any

from app.domain.differences import (
    DatasetComparison,
    ParameterDifference,
    build_dataset_comparison,
    build_parameter_differences,
)


@dataclass(frozen=True)
class AccuracySummary:
    """Available best-accuracy values or a precise unavailable reason."""

    status: str
    unavailable_reason: str | None
    parent_best: float | None
    result_best: float | None
    delta: float | None


@dataclass(frozen=True)
class Comparison:
    """Full immutable-Snapshot comparison for one Evolution Step."""

    status: str
    unavailable_reason: str | None
    parameters: tuple[ParameterDifference, ...]
    accuracy: AccuracySummary
    datasets: DatasetComparison


@dataclass(frozen=True)
class ComparisonSummary:
    """Small list-safe summary derived from the same full comparison result."""

    status: str
    unavailable_reason: str | None
    parameter_change_count: int | None
    accuracy: AccuracySummary
    dataset_status: str
    dataset_unavailable_reason: str | None


def build_comparison(
    parent_run_id: str | None,
    parent_snapshot: dict[str, Any] | None,
    result_run_id: str | None,
    result_snapshot: dict[str, Any] | None,
) -> Comparison:
    """Compare finalized Snapshots after checking prerequisites in fixed order.

    Args:
        parent_run_id: Current parent Run link, if selected.
        parent_snapshot: Immutable parent Snapshot data, if captured.
        result_run_id: Current result Run link, if selected.
        result_snapshot: Immutable result Snapshot data, if captured.

    Returns:
        Comparison: Full differences or one explicit unavailable state.
    """
    unavailable_reason = _comparison_unavailable_reason(
        parent_run_id,
        parent_snapshot,
        result_run_id,
        result_snapshot,
    )
    if unavailable_reason is not None:
        return _unavailable_comparison(unavailable_reason)

    parent_values = parent_snapshot if parent_snapshot is not None else {}
    result_values = result_snapshot if result_snapshot is not None else {}
    return Comparison(
        status="available",
        unavailable_reason=None,
        parameters=build_parameter_differences(
            parent_values.get("parameters", {}),
            result_values.get("parameters", {}),
        ),
        accuracy=_accuracy_summary(
            parent_values.get("best_accuracy"),
            result_values.get("best_accuracy"),
        ),
        datasets=build_dataset_comparison(
            parent_values.get("datasets", ()),
            result_values.get("datasets", ()),
        ),
    )


def build_comparison_summary(
    parent_snapshot: dict[str, Any] | None,
    result_snapshot: dict[str, Any] | None,
    parent_run_id: str | None = "summary-parent",
    result_run_id: str | None = "summary-result",
) -> ComparisonSummary:
    """Build a compact list summary from the same detailed comparison rules.

    Args:
        parent_snapshot: Immutable parent Snapshot values, if captured.
        result_snapshot: Immutable result Snapshot values, if captured.
        parent_run_id: Parent link used to distinguish absent links from pending data.
        result_run_id: Result link used to distinguish absent links from pending data.

    Returns:
        ComparisonSummary: List-safe fields without full Parameter/Dataset differences.
    """
    comparison = build_comparison(
        parent_run_id,
        parent_snapshot,
        result_run_id,
        result_snapshot,
    )
    return ComparisonSummary(
        status=comparison.status,
        unavailable_reason=comparison.unavailable_reason,
        parameter_change_count=(len(comparison.parameters) if comparison.status == "available" else None),
        accuracy=comparison.accuracy,
        dataset_status=comparison.datasets.status,
        dataset_unavailable_reason=comparison.datasets.unavailable_reason,
    )


def _comparison_unavailable_reason(
    parent_run_id: str | None,
    parent_snapshot: dict[str, Any] | None,
    result_run_id: str | None,
    result_snapshot: dict[str, Any] | None,
) -> str | None:
    """Return the first unmet full-comparison prerequisite in documented order.

    Args:
        parent_run_id: Optional parent Run link.
        parent_snapshot: Optional captured parent Snapshot.
        result_run_id: Optional result Run link.
        result_snapshot: Optional captured result Snapshot.

    Returns:
        str | None: First unavailable reason, or ``None`` when both Snapshots exist.
    """
    if parent_run_id is None:
        return "parent_run_missing"
    if result_run_id is None:
        return "result_run_missing"
    if parent_snapshot is None:
        return "parent_snapshot_pending"
    if result_snapshot is None:
        return "result_snapshot_pending"
    return None


def _unavailable_comparison(reason: str) -> Comparison:
    """Build mutually consistent child states for an unavailable full comparison.

    Args:
        reason: Documented reason the overall comparison cannot be calculated.

    Returns:
        Comparison: Empty values with child reasons tied to the overall state.
    """
    return Comparison(
        status="unavailable",
        unavailable_reason=reason,
        parameters=(),
        accuracy=AccuracySummary("unavailable", "comparison_unavailable", None, None, None),
        datasets=DatasetComparison("unavailable", "comparison_unavailable", ()),
    )


def _accuracy_summary(parent_best: object, result_best: object) -> AccuracySummary:
    """Return valid accuracy ratios or the precise side that lacks one.

    Args:
        parent_best: Parent Snapshot best-accuracy value.
        result_best: Result Snapshot best-accuracy value.

    Returns:
        AccuracySummary: Available ratios or an accuracy-specific unavailable state.
    """
    parent_accuracy = _valid_accuracy(parent_best)
    result_accuracy = _valid_accuracy(result_best)
    if parent_accuracy is None and result_accuracy is None:
        return AccuracySummary("unavailable", "both_accuracy_values_missing", None, None, None)
    if parent_accuracy is None:
        return AccuracySummary("unavailable", "parent_accuracy_missing", None, None, None)
    if result_accuracy is None:
        return AccuracySummary("unavailable", "result_accuracy_missing", None, None, None)
    return AccuracySummary(
        "available",
        None,
        parent_accuracy,
        result_accuracy,
        round(result_accuracy - parent_accuracy, 12),
    )


def _valid_accuracy(value: object) -> float | None:
    """Accept only finite Snapshot accuracy ratios in the documented range.

    Args:
        value: Untrusted Snapshot value to evaluate as an accuracy ratio.

    Returns:
        float | None: Valid ratio from zero through one, or ``None``.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    accuracy = float(value)
    if not 0 <= accuracy <= 1:
        return None
    return accuracy
