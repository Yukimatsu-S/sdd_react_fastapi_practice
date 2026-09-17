"""Verify the public API error contract through the actual application."""

from fastapi.testclient import TestClient


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
