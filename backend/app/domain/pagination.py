"""Opaque, deterministic keyset pagination helpers for Evolution Step lists."""

import base64
import binascii
import json
from datetime import datetime


def encode_cursor(created_at: datetime, evolution_step_id: int) -> str:
    """Encode one ordering boundary without exposing query syntax.

    Args:
        created_at: UTC creation timestamp of the last returned Step.
        evolution_step_id: Positive ID used to break equal-timestamp ties.

    Returns:
        URL-safe opaque continuation token.
    """
    payload = {"createdAt": created_at.isoformat(), "id": evolution_step_id}
    encoded = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(encoded).decode().rstrip("=")


def decode_cursor(token: str) -> tuple[datetime, int]:
    """Decode and validate one opaque list continuation token.

    Args:
        token: Token returned by a preceding list response.

    Returns:
        Tuple of creation timestamp and positive Evolution Step ID.

    Raises:
        ValueError: If the token is empty, malformed, or has invalid fields.
    """
    try:
        padding = "=" * (-len(token) % 4)
        payload = json.loads(base64.urlsafe_b64decode(token + padding))
        created_at = datetime.fromisoformat(payload["createdAt"])
        evolution_step_id = payload["id"]
    except (KeyError, TypeError, ValueError, binascii.Error, json.JSONDecodeError) as error:
        raise ValueError("invalid page token") from error

    if not isinstance(evolution_step_id, int) or isinstance(evolution_step_id, bool) or evolution_step_id < 1:
        raise ValueError("invalid page token")
    if created_at.tzinfo is None:
        raise ValueError("invalid page token")
    return created_at, evolution_step_id


def is_after_cursor(
    created_at: datetime,
    evolution_step_id: int,
    cursor_created_at: datetime,
    cursor_evolution_step_id: int,
) -> bool:
    """Return whether a row belongs after a descending timestamp/ID boundary.

    Args:
        created_at: Candidate row creation time.
        evolution_step_id: Candidate row ID.
        cursor_created_at: Last returned row creation time.
        cursor_evolution_step_id: Last returned row ID.

    Returns:
        Whether the candidate is older in `created_at DESC, id DESC` order.
    """
    return created_at < cursor_created_at or (
        created_at == cursor_created_at and evolution_step_id < cursor_evolution_step_id
    )
