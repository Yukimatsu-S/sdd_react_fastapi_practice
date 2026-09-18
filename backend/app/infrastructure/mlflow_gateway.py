"""Normalized transfer types and protocols at the MLflow integration boundary."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.run_snapshot import MetricObservation


@dataclass(frozen=True)
class RunCandidate:
    """One MLflow Run eligible for selection in an Evolution Step form."""

    run_id: str
    run_name: str | None
    mlflow_experiment_id: str
    mlflow_experiment_name: str
    status: str
    started_at: datetime | None
    ended_at: datetime | None


@dataclass(frozen=True)
class RunCandidatePage:
    """One bounded page of ordered Run selection candidates."""

    items: tuple[RunCandidate, ...]
    next_page_token: str | None


@dataclass(frozen=True)
class DatasetInputPayload:
    """Dataset Input metadata retained when a terminal Run Snapshot is captured."""

    name: str
    digest: str
    source_type: str
    source: str
    schema: str | None
    profile: str | None
    context: str | None


@dataclass(frozen=True)
class RunSnapshotPayload:
    """Immutable terminal data prepared before persistence begins."""

    parameters: dict[str, str]
    metrics: tuple[MetricObservation, ...]
    datasets: tuple[DatasetInputPayload, ...]


@dataclass(frozen=True)
class LoadedRun:
    """Current Run metadata plus optional terminal Snapshot payload."""

    run_id: str
    mlflow_experiment_id: str | None
    run_name: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    snapshot_payload: RunSnapshotPayload | None


class RunSearchGateway(Protocol):
    """Search MLflow for selectable active-lifecycle Runs."""

    def search(self, query: str | None, page_token: str | None) -> RunCandidatePage:
        """Return one deterministic page of candidate Runs."""


class RunLoaderGateway(Protocol):
    """Load the current metadata and optional terminal payload for one Run."""

    def load(self, run_id: str) -> LoadedRun:
        """Return one MLflow Run in the application's normalized representation."""
