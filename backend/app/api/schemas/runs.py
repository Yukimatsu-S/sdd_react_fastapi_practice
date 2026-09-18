"""HTTP response schemas for MLflow Run search, sync, and local Metrics."""

from datetime import datetime

from app.api.schemas.evolution_steps import ApiModel, LinkedRunResponse


class RunCandidateResponse(ApiModel):
    """One MLflow Run candidate available for selection."""

    run_id: str
    run_name: str | None
    mlflow_experiment_id: str
    mlflow_experiment_name: str
    status: str
    started_at: datetime | None
    ended_at: datetime | None


class RunCandidatePageResponse(ApiModel):
    """One bounded, server-token-paginated Run candidate page."""

    items: list[RunCandidateResponse]
    next_page_token: str | None


class RunSyncResponse(ApiModel):
    """Latest locally saved Reference and optional captured Snapshot."""

    run: LinkedRunResponse


class BestStepMetricItemResponse(ApiModel):
    """One canonical Metric captured at the selected best-accuracy step."""

    name: str
    value: float
    step: int
    recorded_at: datetime


class BestStepMetricsResponse(ApiModel):
    """Available local Metrics or a reason why the Run has none yet."""

    run_id: str
    status: str
    unavailable_reason: str | None
    best_accuracy: float | None
    best_accuracy_step: int | None
    best_accuracy_recorded_at: datetime | None
    items: list[BestStepMetricItemResponse]
