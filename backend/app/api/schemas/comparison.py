"""HTTP response schemas for complete immutable-Snapshot comparisons."""

from typing import Literal

from app.api.schemas.evolution_steps import ApiModel


class ParameterDifferenceResponse(ApiModel):
    """One added, changed, or removed Parameter from two Snapshots."""

    name: str
    status: Literal["added", "changed", "removed"]
    parent_value: str | None
    result_value: str | None


class AccuracyComparisonResponse(ApiModel):
    """Available best accuracy ratios or an explicit unavailable state."""

    status: Literal["available", "unavailable"]
    unavailable_reason: Literal[
        "comparison_unavailable",
        "parent_accuracy_missing",
        "result_accuracy_missing",
        "both_accuracy_values_missing",
    ] | None
    parent_best: float | None
    result_best: float | None
    delta: float | None


class DatasetIdentifierResponse(ApiModel):
    """Dataset identity fields from one side of a Snapshot comparison."""

    name: str
    digest: str
    source_type: str
    source: str
    context: str | None


class DatasetDifferenceResponse(ApiModel):
    """One changed or one-sided Dataset Input; never a data-row difference."""

    status: Literal["changed", "parent_only", "result_only"]
    parent: DatasetIdentifierResponse | None
    result: DatasetIdentifierResponse | None
    changed_fields: list[Literal["digest", "sourceType", "source"]]


class DatasetComparisonResponse(ApiModel):
    """Dataset Input differences or an explicit reason they are unavailable."""

    status: Literal["changed", "unchanged", "unavailable"]
    unavailable_reason: Literal[
        "comparison_unavailable",
        "parent_dataset_inputs_missing",
        "result_dataset_inputs_missing",
        "both_dataset_inputs_missing",
        "dataset_pairing_ambiguous",
    ] | None
    differences: list[DatasetDifferenceResponse]


class ComparisonResponse(ApiModel):
    """Full immutable-Snapshot comparison returned for one Evolution Step."""

    status: Literal["available", "unavailable"]
    unavailable_reason: Literal[
        "parent_run_missing",
        "result_run_missing",
        "parent_snapshot_pending",
        "result_snapshot_pending",
    ] | None
    parameters: list[ParameterDifferenceResponse]
    accuracy: AccuracyComparisonResponse
    datasets: DatasetComparisonResponse
