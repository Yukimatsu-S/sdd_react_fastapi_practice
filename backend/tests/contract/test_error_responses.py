"""Verify the public API error contract through the actual application."""

import json
from collections.abc import Iterator

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.errors import ApiError, api_error_handler


@pytest.mark.parametrize("status_code", [404, 409, 422, 502])
def test_direct_handler_preserves_error_and_trace_id(status_code: int) -> None:
    """Preserve supplied error information without hard-coding one status.

    Args:
        status_code: Expected HTTP status supplied by the caller.
    """
    request = Request({"type": "http"})
    request.state.trace_id = "trace-test-001"
    error = ApiError(
        status_code=status_code,
        code="example_error",
        message="Example public error message.",
    )

    response = api_error_handler(request, error)

    assert response.status_code == status_code
    assert json.loads(response.body) == {
        "code": "example_error",
        "message": "Example public error message.",
        "traceId": "trace-test-001",
    }


def test_unknown_api_route_returns_error_envelope(client: TestClient) -> None:
    """Require the common error fields for an unregistered API route.

    Args:
        client: HTTP client connected to the actual FastAPI application.
    """
    response = client.get("/api/v1/unknown")

    assert response.status_code == 404
    body = response.json()
    assert "code" in body
    assert isinstance(body["code"], str) and body["code"]
    assert "message" in body
    assert isinstance(body["message"], str) and body["message"]
    assert "traceId" in body
    assert isinstance(body["traceId"], str) and body["traceId"]


@pytest.fixture
def error_client(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """Temporarily add error probes without registering product handlers.

    Args:
        client: Client for the real application and its actual middleware.
        monkeypatch: Restore the original route list after the test.

    Yields:
        TestClient: Client with test-only routes, requiring no DB or MLflow.
    """
    from main import app

    monkeypatch.setattr(app.router, "routes", list(app.router.routes))
    router = APIRouter(prefix="/api/v1/_test")

    @router.get("/expected/{status_code}")
    def expected_error(status_code: int) -> None:
        """Raise a controlled failure for the HTTP registration test.

        Args:
            status_code: Status carried by the test exception.

        Raises:
            ApiError: Always, with fixed public test information.
        """
        raise ApiError(status_code, "example_error", "Example public error message.")

    @router.get("/unexpected")
    def unexpected_error() -> None:
        """Raise an internal failure that must not leak to the response.

        Raises:
            RuntimeError: Always, with a recognizable internal test detail.
        """
        raise RuntimeError("private-test-diagnostic")

    app.include_router(router)
    yield client


@pytest.mark.parametrize("status_code", [409, 502])
def test_expected_error_uses_registered_handler(
    error_client: TestClient, status_code: int,
) -> None:
    """Verify application registration, not just direct serialization.

    Args:
        error_client: Real application client with temporary error routes.
        status_code: Conflict or upstream-failure status to preserve.
    """
    response = error_client.get(f"/api/v1/_test/expected/{status_code}")

    assert response.status_code == status_code
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["code"] == "example_error"
    assert body["message"] == "Example public error message."
    assert isinstance(body["traceId"], str) and body["traceId"]


def test_validation_error_returns_error_envelope(error_client: TestClient) -> None:
    """Require the common envelope for FastAPI input validation failures.

    Args:
        error_client: Real application client with an integer path parameter.
    """
    response = error_client.get("/api/v1/_test/expected/not-an-integer")

    assert response.status_code == 422
    body = response.json()
    assert "code" in body
    assert isinstance(body["code"], str) and body["code"]
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["traceId"], str) and body["traceId"]


def test_unexpected_error_returns_safe_envelope(error_client: TestClient) -> None:
    """Return a traceable JSON error without exposing internal diagnostics.

    Args:
        error_client: Real application client with an unexpected-error route.
    """
    response = error_client.get("/api/v1/_test/unexpected")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert isinstance(body["code"], str) and body["code"]
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["traceId"], str) and body["traceId"]
    assert "private-test-diagnostic" not in response.text


def test_separate_requests_receive_distinct_trace_ids(client: TestClient) -> None:
    """Distinguish separate failed requests instead of returning a fixed ID.

    Args:
        client: Client for the actual application.
    """
    first_response = client.get("/api/v1/unknown")
    second_response = client.get("/api/v1/unknown")

    assert first_response.status_code == second_response.status_code == 404
    first_body = first_response.json()
    second_body = second_response.json()
    assert "traceId" in first_body
    assert "traceId" in second_body
    assert isinstance(first_body["traceId"], str) and first_body["traceId"]
    assert isinstance(second_body["traceId"], str) and second_body["traceId"]
    assert first_body["traceId"] != second_body["traceId"]
