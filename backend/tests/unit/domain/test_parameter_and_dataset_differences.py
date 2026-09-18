"""Specify Parameter and Dataset Input comparison rules before implementation."""

from app.domain.differences import (
    build_dataset_comparison,
    build_parameter_differences,
)
from app.infrastructure.run_repository import DatasetInputRecord


def _dataset(
    ordinal: int,
    name: str,
    digest: str,
    source_type: str = "s3",
    source: str = "s3://datasets/training.csv",
    context: str | None = "training",
) -> DatasetInputRecord:
    """Create one captured Dataset Input with readable test defaults.

    Args:
        ordinal: Position recorded by MLflow within one Run Snapshot.
        name: Dataset name recorded by MLflow.
        digest: Dataset content identifier recorded by MLflow.
        source_type: Kind of source that supplied the Dataset.
        source: Source identifier recorded by MLflow.
        context: Dataset usage context recorded by MLflow.

    Returns:
        DatasetInputRecord: Immutable Dataset Input used by a test Snapshot.
    """
    return DatasetInputRecord(
        ordinal=ordinal,
        name=name,
        digest=digest,
        source_type=source_type,
        source=source,
        context=context,
    )


def test_parameter_differences_include_only_added_changed_and_removed_values() -> None:
    """Compare the union of Parameter names in deterministic name order."""
    differences = build_parameter_differences(
        parent_parameters={"batch_size": "32", "epochs": "10", "learning_rate": "0.01"},
        result_parameters={"epochs": "20", "learning_rate": "0.01", "optimizer": "adamw"},
    )

    assert [
        (item.name, item.status, item.parent_value, item.result_value)
        for item in differences
    ] == [
        ("batch_size", "removed", "32", None),
        ("epochs", "changed", "10", "20"),
        ("optimizer", "added", None, "adamw"),
    ]


def test_dataset_comparison_reports_changed_and_one_sided_inputs() -> None:
    """Use unique context/name pairs and report only meaningful differences."""
    comparison = build_dataset_comparison(
        parent_datasets=(
            _dataset(0, "images", "digest-v1"),
            _dataset(1, "labels", "labels-v1"),
        ),
        result_datasets=(
            _dataset(0, "images", "digest-v2", source="s3://datasets/images-v2.csv"),
            _dataset(1, "weights", "weights-v1"),
        ),
    )

    assert comparison.status == "changed"
    assert comparison.unavailable_reason is None
    assert [
        (
            item.status,
            item.parent.name if item.parent is not None else None,
            item.result.name if item.result is not None else None,
            item.changed_fields,
        )
        for item in comparison.differences
    ] == [
        ("changed", "images", "images", ("digest", "source")),
        ("parent_only", "labels", None, ()),
        ("result_only", None, "weights", ()),
    ]


def test_dataset_comparison_is_unavailable_when_a_snapshot_has_no_inputs() -> None:
    """Never label an empty Dataset Input collection as unchanged."""
    comparison = build_dataset_comparison(
        parent_datasets=(),
        result_datasets=(_dataset(0, "images", "digest-v1"),),
    )

    assert comparison.status == "unavailable"
    assert comparison.unavailable_reason == "parent_dataset_inputs_missing"
    assert comparison.differences == ()


def test_dataset_comparison_is_unavailable_when_pairing_key_is_ambiguous() -> None:
    """Refuse to guess when one context/name pair occurs more than once."""
    comparison = build_dataset_comparison(
        parent_datasets=(
            _dataset(0, "images", "digest-v1"),
            _dataset(1, "images", "digest-v2"),
        ),
        result_datasets=(_dataset(0, "images", "digest-v3"),),
    )

    assert comparison.status == "unavailable"
    assert comparison.unavailable_reason == "dataset_pairing_ambiguous"
    assert comparison.differences == ()
