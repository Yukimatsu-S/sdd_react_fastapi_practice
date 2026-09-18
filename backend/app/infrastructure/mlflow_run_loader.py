"""MLflow-backed current Run loading and terminal Snapshot payload preparation."""

from datetime import UTC, datetime
from typing import Any

from app.domain.run_snapshot import MetricObservation
from app.infrastructure.mlflow_gateway import (
    DatasetInputPayload,
    LoadedRun,
    RunSnapshotPayload,
)

TERMINAL_STATUSES = {"FINISHED", "FAILED", "KILLED"}


class MlflowRunLoader:
    """Adapt one MLflow Run to current metadata and optional terminal details."""

    def __init__(self, client: Any) -> None:
        """Store the MLflow-compatible client used for read-only loading.

        Args:
            client: MLflow client or an in-memory test fake with matching methods.
        """
        self._client = client

    def load(self, run_id: str) -> LoadedRun:
        """Load current metadata and capture payload only for a terminal Run.

        Args:
            run_id: MLflow Run identifier selected by the caller.

        Returns:
            LoadedRun: Current display metadata and terminal capture data when eligible.
        """
        raw_run = self._client.get_run(run_id)
        info = getattr(raw_run, "info", None)
        status = str(_run_field(raw_run, info, "status"))
        snapshot_payload = None
        if status in TERMINAL_STATUSES:
            snapshot_payload = _snapshot_payload(raw_run, self._client)

        data = getattr(raw_run, "data", None)
        tags = getattr(data, "tags", {}) if data is not None else {}
        run_name = getattr(raw_run, "run_name", None) or tags.get("mlflow.runName")
        ended_at_value = _run_field(raw_run, info, "end_time")
        return LoadedRun(
            run_id=str(_run_field(raw_run, info, "run_id")),
            mlflow_experiment_id=str(_run_field(raw_run, info, "experiment_id")),
            run_name=None if run_name is None else str(run_name),
            status=status,
            started_at=_to_datetime(_run_field(raw_run, info, "start_time")),
            ended_at=None if ended_at_value is None else _to_datetime(ended_at_value),
            snapshot_payload=snapshot_payload,
        )


def _snapshot_payload(raw_run: Any, client: Any) -> RunSnapshotPayload:
    """Normalize terminal Parameters, Metric histories, and Dataset Inputs.

    Args:
        raw_run: Terminal MLflow Run object or test fake.
        client: Source used to read full Metric history for each Metric name.

    Returns:
        RunSnapshotPayload: Immutable data prepared before database persistence.
    """
    data = getattr(raw_run, "data", None)
    parameters = dict(getattr(raw_run, "parameters", getattr(data, "params", {})))
    metric_names = _metric_names(raw_run, data)
    metrics = tuple(
        MetricObservation(
            name=str(metric.key),
            value=float(metric.value),
            step=int(metric.step),
            recorded_at=_to_datetime(metric.timestamp),
        )
        for metric_name in metric_names
        for metric in client.get_metric_history(_run_id(raw_run), metric_name)
    )
    raw_datasets = getattr(raw_run, "datasets", None)
    if raw_datasets is None:
        raw_datasets = getattr(getattr(raw_run, "inputs", None), "dataset_inputs", ())
    datasets = tuple(_to_dataset_payload(item) for item in raw_datasets)
    return RunSnapshotPayload(parameters=parameters, metrics=metrics, datasets=datasets)


def _metric_names(raw_run: Any, data: Any) -> tuple[str, ...]:
    """Read Metric names from either a real MLflow Run or a test fake.

    Args:
        raw_run: MLflow-shaped Run that may expose full fake history.
        data: Optional MLflow RunData object.

    Returns:
        tuple[str, ...]: Deterministically ordered Metric names.
    """
    fake_metrics = getattr(raw_run, "metrics", None)
    if fake_metrics is not None:
        return tuple(sorted({metric.key for metric in fake_metrics}))
    return tuple(sorted(getattr(data, "metrics", {})))


def _to_dataset_payload(raw_dataset: Any) -> DatasetInputPayload:
    """Normalize one MLflow-shaped Dataset Input record.

    Args:
        raw_dataset: Dataset Input object or a test fake.

    Returns:
        DatasetInputPayload: Stored dataset identity fields.
    """
    dataset = getattr(raw_dataset, "dataset", raw_dataset)
    return DatasetInputPayload(
        name=str(dataset.name),
        digest=str(dataset.digest),
        source_type=str(dataset.source_type),
        source=str(dataset.source),
        schema=getattr(dataset, "schema", None),
        profile=getattr(dataset, "profile", None),
        context=getattr(raw_dataset, "context", getattr(dataset, "context", None)),
    )


def _run_id(raw_run: Any) -> str:
    """Read a Run ID from a real MLflow Run or the test fake.

    Args:
        raw_run: MLflow-shaped Run containing identifier fields.

    Returns:
        str: Run identifier used for Metric-history retrieval.
    """
    return str(_run_field(raw_run, getattr(raw_run, "info", None), "run_id"))


def _run_field(raw_run: Any, info: Any, name: str) -> Any:
    """Read a field from a real Run's info object or a direct test fake.

    Args:
        raw_run: MLflow Run object or in-memory fake.
        info: Optional real MLflow RunInfo object.
        name: Field name present on RunInfo or the fake Run.

    Returns:
        Any: Field value from the real RunInfo or the direct fake field.
    """
    if info is not None and hasattr(info, name):
        return getattr(info, name)
    return getattr(raw_run, name)


def _to_datetime(value: datetime | int) -> datetime:
    """Normalize an MLflow millisecond timestamp or fake datetime to UTC.

    Args:
        value: Timestamp supplied by MLflow or the test fake.

    Returns:
        datetime: UTC-aware timestamp used by the application.
    """
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    return datetime.fromtimestamp(value / 1000, tz=UTC)
