"""Specify pure Evolution Step text and terminal Snapshot selection rules."""

from datetime import UTC, datetime

import pytest

from app.domain.evolution_step import validate_change_description, validate_required_text
from app.domain.run_snapshot import (
    MetricObservation,
    canonicalize_metric_observations,
    select_best_step_metrics,
)


@pytest.mark.parametrize("value", ["", "   ", "\t", "\n"])
def test_required_evolution_step_text_rejects_blank_values(value: str) -> None:
    """Reject empty or whitespace-only purpose and hypothesis values.

    Args:
        value: Invalid text submitted for a required field.
    """
    with pytest.raises(ValueError, match="purpose"):
        validate_required_text(value, "purpose")

    with pytest.raises(ValueError, match="hypothesis"):
        validate_required_text(value, "hypothesis")


def test_change_description_allows_none_but_rejects_blank_text() -> None:
    """Distinguish an explicit clear from an invalid empty supplied value."""
    assert validate_change_description(None) is None

    with pytest.raises(ValueError, match="change_description"):
        validate_change_description("  ")


def test_canonical_metrics_choose_latest_timestamp_then_largest_value() -> None:
    """Keep one deterministic observation for each Metric name and signed step."""
    earlier = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)
    latest = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
    observations = [
        MetricObservation("accuracy", 0.80, -1, earlier),
        MetricObservation("accuracy", 0.90, -1, latest),
        MetricObservation("accuracy", 0.92, -1, latest),
        MetricObservation("loss", 0.40, -1, latest),
    ]

    canonical = canonicalize_metric_observations(observations)

    assert canonical == (
        MetricObservation("accuracy", 0.92, -1, latest),
        MetricObservation("loss", 0.40, -1, latest),
    )


def test_best_accuracy_uses_smallest_signed_step_and_only_that_steps_metrics() -> None:
    """Select the smallest step that has the canonical maximum accuracy."""
    first = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)
    second = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
    selection = select_best_step_metrics(
        [
            MetricObservation("accuracy", 0.90, 0, first),
            MetricObservation("accuracy", 0.95, 5, second),
            MetricObservation("loss", 0.30, 5, second),
            MetricObservation("accuracy", 0.95, -1, second),
            MetricObservation("precision", 0.88, -1, second),
        ],
    )

    assert selection.best_accuracy == 0.95
    assert selection.best_accuracy_step == -1
    assert selection.best_accuracy_recorded_at == second
    assert selection.metrics == (
        MetricObservation("accuracy", 0.95, -1, second),
        MetricObservation("precision", 0.88, -1, second),
    )


def test_snapshot_selection_has_no_best_step_when_accuracy_is_absent() -> None:
    """Keep Parameters and Datasets eligible for capture without invented Metrics."""
    recorded_at = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)

    selection = select_best_step_metrics([MetricObservation("loss", 0.30, 3, recorded_at)])

    assert selection.best_accuracy is None
    assert selection.best_accuracy_step is None
    assert selection.best_accuracy_recorded_at is None
    assert selection.metrics == ()
