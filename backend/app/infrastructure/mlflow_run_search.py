"""MLflow-backed candidate search with deterministic local paging."""

import base64
import json
from datetime import UTC, datetime
from typing import Any

from mlflow.entities import ViewType

from app.infrastructure.mlflow_gateway import RunCandidate, RunCandidatePage

PAGE_SIZE = 20


class MlflowRunSearch:
    """Adapt MLflow Experiment and Run records into selectable candidate pages."""

    def __init__(self, client: Any) -> None:
        """Store the MLflow-compatible client used for read-only search.

        Args:
            client: MLflow client or an in-memory test fake with matching methods.
        """
        self._client = client

    def search(self, query: str | None, page_token: str | None) -> RunCandidatePage:
        """Return one stable page of active-lifecycle candidates.

        Args:
            query: Optional case-insensitive Run-name substring.
            page_token: Opaque cursor from the preceding candidate page.

        Returns:
            RunCandidatePage: At most 20 ordered items and a continuation token.

        Raises:
            ValueError: If the supplied page token is malformed.
        """
        experiments = self._client.search_experiments(view_type=ViewType.ACTIVE_ONLY)
        experiment_names = {
            str(experiment.experiment_id): str(experiment.name)
            for experiment in experiments
        }
        if not experiment_names:
            return RunCandidatePage((), None)

        raw_runs = self._client.search_runs(
            experiment_ids=list(experiment_names),
            run_view_type=ViewType.ACTIVE_ONLY,
            max_results=1000,
        )
        candidates = [
            candidate
            for candidate in (
                _to_candidate(raw_run, experiment_names) for raw_run in raw_runs
            )
            if candidate is not None and _matches_query(candidate, query)
        ]
        candidates.sort(key=lambda item: (-item.started_at.timestamp(), item.run_id))

        cursor = _decode_page_token(page_token)
        if cursor is not None:
            candidates = [item for item in candidates if _comes_after(item, cursor)]

        page_items = tuple(candidates[:PAGE_SIZE])
        next_page_token = None
        if len(candidates) > PAGE_SIZE:
            last_item = page_items[-1]
            next_page_token = _encode_page_token(last_item)
        return RunCandidatePage(page_items, next_page_token)


def _to_candidate(raw_run: Any, experiment_names: dict[str, str]) -> RunCandidate | None:
    """Normalize one MLflow-shaped Run and discard deleted lifecycle records.

    Args:
        raw_run: MLflow Run object or an in-memory fake with equivalent fields.
        experiment_names: Active Experiment names indexed by Experiment ID.

    Returns:
        RunCandidate | None: Candidate when active, otherwise None.
    """
    info = getattr(raw_run, "info", None)
    lifecycle_stage = str(_run_field(raw_run, info, "lifecycle_stage")).lower()
    if lifecycle_stage != "active":
        return None

    experiment_id = str(_run_field(raw_run, info, "experiment_id"))
    data = getattr(raw_run, "data", None)
    tags = getattr(data, "tags", {}) if data is not None else {}
    run_name = getattr(raw_run, "run_name", None) or tags.get("mlflow.runName")
    started_at = _to_datetime(_run_field(raw_run, info, "start_time"))
    ended_at_value = _run_field(raw_run, info, "end_time")
    return RunCandidate(
        run_id=str(_run_field(raw_run, info, "run_id")),
        run_name=None if run_name is None else str(run_name),
        mlflow_experiment_id=experiment_id,
        mlflow_experiment_name=experiment_names[experiment_id],
        status=str(_run_field(raw_run, info, "status")),
        started_at=started_at,
        ended_at=None if ended_at_value is None else _to_datetime(ended_at_value),
    )


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


def _matches_query(candidate: RunCandidate, query: str | None) -> bool:
    """Apply optional case-insensitive name filtering to one candidate.

    Args:
        candidate: Candidate to include or exclude.
        query: Optional substring entered by the user.

    Returns:
        bool: Whether the candidate's Run name matches the query.
    """
    return query is None or query.casefold() in (candidate.run_name or "").casefold()


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


def _encode_page_token(candidate: RunCandidate) -> str:
    """Encode the final candidate in a page as an opaque continuation cursor.

    Args:
        candidate: Last candidate returned to the browser.

    Returns:
        str: URL-safe cursor containing only ordering fields.
    """
    payload = json.dumps(
        {"startedAt": candidate.started_at.isoformat(), "runId": candidate.run_id},
        separators=(",", ":"),
    )
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_page_token(page_token: str | None) -> tuple[datetime, str] | None:
    """Decode a candidate cursor without exposing its format to API callers.

    Args:
        page_token: Opaque token from a preceding search response.

    Returns:
        tuple[datetime, str] | None: Cursor timestamp and Run ID, or None initially.

    Raises:
        ValueError: If a supplied token cannot be decoded into ordering fields.
    """
    if page_token is None:
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(page_token.encode()).decode())
        return datetime.fromisoformat(payload["startedAt"]), str(payload["runId"])
    except (KeyError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("page token is invalid") from error


def _comes_after(candidate: RunCandidate, cursor: tuple[datetime, str]) -> bool:
    """Decide whether a candidate follows a cursor in the documented order.

    Args:
        candidate: Candidate considered for the next page.
        cursor: Timestamp and Run ID of the preceding page's final item.

    Returns:
        bool: Whether the candidate belongs after the cursor.
    """
    cursor_time, cursor_run_id = cursor
    return candidate.started_at < cursor_time or (
        candidate.started_at == cursor_time and candidate.run_id > cursor_run_id
    )
