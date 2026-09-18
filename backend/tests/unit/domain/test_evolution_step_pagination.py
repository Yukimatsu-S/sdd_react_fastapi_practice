"""Define stable opaque pagination rules before persistence reads use them."""

from datetime import UTC, datetime

import pytest

from app.domain.pagination import decode_cursor, encode_cursor, is_after_cursor


def test_cursor_round_trip_and_descending_tie_breaker() -> None:
    """Round-trip one exact timestamp/ID pair and order equal times by ID."""
    created_at = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)

    token = encode_cursor(created_at, 20)

    assert decode_cursor(token) == (created_at, 20)
    assert is_after_cursor(created_at, 19, created_at, 20)
    assert not is_after_cursor(created_at, 21, created_at, 20)


@pytest.mark.parametrize("token", ["", "not-base64", "eyJpZCI6MH0="])
def test_malformed_cursor_is_rejected(token: str) -> None:
    """Reject empty, undecodable, and structurally incomplete cursor values."""
    with pytest.raises(ValueError, match="page token"):
        decode_cursor(token)
