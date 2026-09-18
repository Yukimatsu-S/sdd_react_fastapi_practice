"""In-memory MLflow-shaped records for gateway tests."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class FakeMetric:
    """One MLflow Metric history observation supplied by a fake Run."""

    key: str
    value: float
    step: int
    timestamp: datetime


@dataclass(frozen=True)
class FakeDataset:
    """One Dataset Input record supplied by a fake terminal Run."""

    name: str
    digest: str
    source_type: str
    source: str
    context: str | None = None


@dataclass(frozen=True)
class FakeRun:
    """Current and terminal-capture fields exposed by a fake MLflow Run."""

    run_id: str
    experiment_id: str
    experiment_name: str
    lifecycle_stage: str
    status: str
    start_time: datetime
    end_time: datetime | None
    run_name: str | None
    parameters: dict[str, str] = field(default_factory=dict)
    metrics: tuple[FakeMetric, ...] = ()
    datasets: tuple[FakeDataset, ...] = ()


class FakeMlflowClient:
    """Offer a small deterministic source for search and Run-loader adapters."""

    def __init__(self, runs: tuple[FakeRun, ...]) -> None:
        """Store fake Runs without making network calls.

        Args:
            runs: All active or deleted Runs exposed to the adapter under test.
        """
        self.runs = runs
        self.last_search_experiment_ids: tuple[str, ...] = ()

    def search_runs(self, experiment_ids: tuple[str, ...]) -> tuple[FakeRun, ...]:
        """Return Runs in the requested Experiments and record the request.

        Args:
            experiment_ids: MLflow Experiment IDs requested by the adapter.

        Returns:
            tuple[FakeRun, ...]: Matching fake Runs in fixture order.
        """
        self.last_search_experiment_ids = experiment_ids
        return tuple(run for run in self.runs if run.experiment_id in experiment_ids)

    def get_run(self, run_id: str) -> FakeRun:
        """Return one fake Run or fail as MLflow would for an unknown ID.

        Args:
            run_id: Run identifier requested by the adapter.

        Returns:
            FakeRun: Matching fake Run.

        Raises:
            KeyError: If the fake source has no matching Run.
        """
        for run in self.runs:
            if run.run_id == run_id:
                return run
        raise KeyError(run_id)
