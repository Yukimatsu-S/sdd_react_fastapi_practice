"""Verify the public API error contract through the actual application."""

import json

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.errors import ApiError, api_error_handler


def test_direct_handler_preserves_error_and_trace_id() -> None:
    """Preserve the supplied error information and request trace ID."""
    request = Request({"type": "http"})
    request.state.trace_id = "trace-test-001"
    error = ApiError(
        status_code=409,
        code="result_run_conflict",
        message="Result Run is already linked to another Evolution Step.",
    )

    response = api_error_handler(request, error)

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "code": "result_run_conflict",
        "message": "Result Run is already linked to another Evolution Step.",
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
