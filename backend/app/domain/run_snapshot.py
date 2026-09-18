"""Canonical Metric selection for immutable Run Snapshot capture."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MetricObservation:
    """One Metric value recorded by MLflow at a signed step and timestamp."""

    name: str
    value: float
    step: int
    recorded_at: datetime


@dataclass(frozen=True)
class BestStepMetricSelection:
    """Best accuracy details and the canonical Metrics from its selected step."""

    best_accuracy: float | None
    best_accuracy_step: int | None
    best_accuracy_recorded_at: datetime | None
    metrics: tuple[MetricObservation, ...]


def canonicalize_metric_observations(
    observations: Iterable[MetricObservation],
) -> tuple[MetricObservation, ...]:
    """Keep the latest, then greatest, value for every Metric name and step.

    Args:
        observations: Potentially repeated MLflow Metric observations.

    Returns:
        tuple[MetricObservation, ...]: Canonical values ordered by name then step.
    """
    selected: dict[tuple[str, int], MetricObservation] = {}
    for observation in observations:
        key = (observation.name, observation.step)
        current = selected.get(key)
        if current is None or (observation.recorded_at, observation.value) > (
            current.recorded_at,
            current.value,
        ):
            selected[key] = observation

    return tuple(selected[key] for key in sorted(selected))


def select_best_step_metrics(
    observations: Iterable[MetricObservation],
) -> BestStepMetricSelection:
    """Select the minimum step tied for best canonical accuracy and its Metrics.

    Args:
        observations: Metric observations available when a terminal Run is captured.

    Returns:
        BestStepMetricSelection: Selected accuracy details and only that step's Metrics.
    """
    canonical = canonicalize_metric_observations(observations)
    accuracy_observations = tuple(item for item in canonical if item.name == "accuracy")
    if not accuracy_observations:
        return BestStepMetricSelection(None, None, None, ())

    best_accuracy = max(item.value for item in accuracy_observations)
    selected_accuracy = min(
        (item for item in accuracy_observations if item.value == best_accuracy),
        key=lambda item: item.step,
    )
    best_step_metrics = tuple(item for item in canonical if item.step == selected_accuracy.step)
    return BestStepMetricSelection(
        best_accuracy=best_accuracy,
        best_accuracy_step=selected_accuracy.step,
        best_accuracy_recorded_at=selected_accuracy.recorded_at,
        metrics=best_step_metrics,
    )
