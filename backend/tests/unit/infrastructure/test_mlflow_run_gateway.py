"""Specify MLflow Run search and load behavior without an external server."""

from datetime import UTC, datetime, timedelta

from app.infrastructure.mlflow_run_loader import MlflowRunLoader
from app.infrastructure.mlflow_run_search import MlflowRunSearch
from tests.fakes.mlflow import FakeDataset, FakeMetric, FakeMlflowClient, FakeRun


def test_search_excludes_deleted_runs_and_keeps_same_time_pages_stable() -> None:
    """Return active Runs by descending time and ascending ID without duplicates."""
    started_at = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
    active_runs = tuple(
        FakeRun(
            run_id=f"run-{index:03d}",
            experiment_id="1",
            experiment_name="images",
            lifecycle_stage="active",
            status="FINISHED",
            start_time=started_at,
            end_time=started_at + timedelta(minutes=1),
            run_name=f"Candidate {index:03d}",
        )
        for index in range(21)
    )
    client = FakeMlflowClient(
        active_runs
        + (
            FakeRun(
                run_id="run-deleted",
                experiment_id="1",
                experiment_name="images",
                lifecycle_stage="deleted",
                status="FINISHED",
                start_time=started_at + timedelta(hours=1),
                end_time=None,
                run_name="Deleted candidate",
            ),
        ),
    )
    search = MlflowRunSearch(client)

    first_page = search.search(query=None, page_token=None)
    second_page = search.search(query=None, page_token=first_page.next_page_token)

    assert [item.run_id for item in first_page.items] == [f"run-{index:03d}" for index in range(20)]
    assert [item.run_id for item in second_page.items] == ["run-020"]
    assert second_page.next_page_token is None
    assert client.last_search_experiment_ids == ("1",)


def test_search_matches_run_names_without_case_sensitivity() -> None:
    """Filter active candidates by case-insensitive Run name substring."""
    started_at = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
    client = FakeMlflowClient(
        (
            FakeRun("run-001", "1", "images", "active", "RUNNING", started_at, None, "Baseline"),
            FakeRun("run-002", "1", "images", "active", "RUNNING", started_at, None, "Augment"),
        ),
    )

    page = MlflowRunSearch(client).search(query="LINE", page_token=None)

    assert [item.run_id for item in page.items] == ["run-001"]


def test_loader_keeps_active_runs_pending_and_captures_terminal_payloads() -> None:
    """Separate current Run metadata from terminal Snapshot capture details."""
    started_at = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
    terminal_at = started_at + timedelta(hours=1)
    client = FakeMlflowClient(
        (
            FakeRun("run-active", "1", "images", "active", "RUNNING", started_at, None, "Active"),
            FakeRun(
                "run-terminal",
                "1",
                "images",
                "active",
                "FINISHED",
                started_at,
                terminal_at,
                "Terminal",
                parameters={"epochs": "20"},
                metrics=(FakeMetric("accuracy", 0.92, 5, terminal_at),),
                datasets=(FakeDataset("training", "digest-v1", "uri", "s3://bucket/train"),),
            ),
        ),
    )
    loader = MlflowRunLoader(client)

    active = loader.load("run-active")
    terminal = loader.load("run-terminal")

    assert active.snapshot_payload is None
    assert terminal.snapshot_payload is not None
    assert terminal.snapshot_payload.parameters == {"epochs": "20"}
    assert terminal.snapshot_payload.metrics[0].name == "accuracy"
    assert terminal.snapshot_payload.datasets[0].digest == "digest-v1"
