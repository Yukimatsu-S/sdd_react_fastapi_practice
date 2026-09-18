"""Pure difference rules for immutable Run Snapshot data."""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


class DatasetInput(Protocol):
    """Captured Dataset fields needed to compare two Snapshot inputs."""

    name: str
    digest: str
    source_type: str
    source: str
    context: str | None


@dataclass(frozen=True)
class ParameterDifference:
    """One added, changed, or removed captured Parameter."""

    name: str
    status: str
    parent_value: str | None
    result_value: str | None


@dataclass(frozen=True)
class DatasetIdentifier:
    """The Dataset identity fields returned for one comparison side."""

    name: str
    digest: str
    source_type: str
    source: str
    context: str | None


@dataclass(frozen=True)
class DatasetDifference:
    """One changed or one-sided Dataset Input; never a row-level difference."""

    status: str
    parent: DatasetIdentifier | None
    result: DatasetIdentifier | None
    changed_fields: tuple[str, ...]


@dataclass(frozen=True)
class DatasetComparison:
    """Dataset comparison result or an explicit reason it cannot be calculated."""

    status: str
    unavailable_reason: str | None
    differences: tuple[DatasetDifference, ...]


def build_parameter_differences(
    parent_parameters: Mapping[str, str],
    result_parameters: Mapping[str, str],
) -> tuple[ParameterDifference, ...]:
    """Return only added, changed, and removed Parameters by name.

    Args:
        parent_parameters: Immutable Parameter values from the parent Snapshot.
        result_parameters: Immutable Parameter values from the result Snapshot.

    Returns:
        tuple[ParameterDifference, ...]: Meaningful differences sorted by Parameter name.
    """
    differences: list[ParameterDifference] = []
    for name in sorted(set(parent_parameters) | set(result_parameters)):
        parent_value = parent_parameters.get(name)
        result_value = result_parameters.get(name)
        if name not in parent_parameters:
            differences.append(ParameterDifference(name, "added", None, result_value))
        elif name not in result_parameters:
            differences.append(ParameterDifference(name, "removed", parent_value, None))
        elif parent_value != result_value:
            differences.append(ParameterDifference(name, "changed", parent_value, result_value))
    return tuple(differences)


def build_dataset_comparison(
    parent_datasets: Sequence[DatasetInput],
    result_datasets: Sequence[DatasetInput],
) -> DatasetComparison:
    """Compare uniquely paired Dataset Inputs by context and name.

    Args:
        parent_datasets: Immutable Dataset Inputs from the parent Snapshot.
        result_datasets: Immutable Dataset Inputs from the result Snapshot.

    Returns:
        DatasetComparison: Differences, unchanged state, or a precise unavailable reason.
    """
    missing_reason = _missing_dataset_reason(parent_datasets, result_datasets)
    if missing_reason is not None:
        return DatasetComparison("unavailable", missing_reason, ())

    parent_by_key = _unique_datasets_by_key(parent_datasets)
    result_by_key = _unique_datasets_by_key(result_datasets)
    if parent_by_key is None or result_by_key is None:
        return DatasetComparison("unavailable", "dataset_pairing_ambiguous", ())

    differences = tuple(
        difference
        for key in sorted(set(parent_by_key) | set(result_by_key), key=_sort_key)
        if (
            difference := _dataset_difference(
                parent_by_key.get(key),
                result_by_key.get(key),
            )
        ) is not None
    )
    status = "changed" if differences else "unchanged"
    return DatasetComparison(status, None, differences)


def _missing_dataset_reason(
    parent_datasets: Sequence[DatasetInput],
    result_datasets: Sequence[DatasetInput],
) -> str | None:
    """Return the reason Dataset comparison cannot start with an empty side.

    Args:
        parent_datasets: Parent Snapshot Dataset Inputs.
        result_datasets: Result Snapshot Dataset Inputs.

    Returns:
        str | None: Missing-input reason, or ``None`` when both sides have rows.
    """
    if not parent_datasets and not result_datasets:
        return "both_dataset_inputs_missing"
    if not parent_datasets:
        return "parent_dataset_inputs_missing"
    if not result_datasets:
        return "result_dataset_inputs_missing"
    return None


def _unique_datasets_by_key(
    datasets: Sequence[DatasetInput],
) -> dict[tuple[str | None, str], DatasetInput] | None:
    """Index Dataset Inputs only when every context/name key is unique.

    Args:
        datasets: One Snapshot's captured Dataset Inputs.

    Returns:
        dict[tuple[str | None, str], DatasetInput] | None: Unique key map, or
        ``None`` when pairing would require guessing.
    """
    keys = [(dataset.context, dataset.name) for dataset in datasets]
    if any(count > 1 for count in Counter(keys).values()):
        return None
    return dict(zip(keys, datasets, strict=True))


def _dataset_difference(
    parent: DatasetInput | None,
    result: DatasetInput | None,
) -> DatasetDifference | None:
    """Compare one matched Dataset pair or describe its one-sided presence.

    Args:
        parent: Parent Dataset Input for one unique pairing key, if present.
        result: Result Dataset Input for the same pairing key, if present.

    Returns:
        DatasetDifference | None: Meaningful difference, or ``None`` when unchanged.
    """
    if parent is None:
        return DatasetDifference("result_only", None, _identifier(result), ())
    if result is None:
        return DatasetDifference("parent_only", _identifier(parent), None, ())

    changed_fields = tuple(
        public_name
        for public_name, parent_value, result_value in (
            ("digest", parent.digest, result.digest),
            ("sourceType", parent.source_type, result.source_type),
            ("source", parent.source, result.source),
        )
        if parent_value != result_value
    )
    if not changed_fields:
        return None
    return DatasetDifference("changed", _identifier(parent), _identifier(result), changed_fields)


def _identifier(dataset: DatasetInput) -> DatasetIdentifier:
    """Copy the public identity fields from one captured Dataset Input.

    Args:
        dataset: Captured Dataset Input to expose in a difference.

    Returns:
        DatasetIdentifier: Immutable comparison-side identifier.
    """
    return DatasetIdentifier(
        name=dataset.name,
        digest=dataset.digest,
        source_type=dataset.source_type,
        source=dataset.source,
        context=dataset.context,
    )


def _sort_key(key: tuple[str | None, str]) -> tuple[str, str]:
    """Provide a deterministic order without conflating null and empty contexts.

    Args:
        key: Dataset pairing key of context and name.

    Returns:
        tuple[str, str]: Comparable representation used only for ordering.
    """
    context, name = key
    return ("" if context is None else context, name)
