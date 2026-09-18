"""Public error types and response conversion for the API boundary."""

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Carry an expected failure's HTTP status and public error information."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        """Store the information that the API handler must serialize.

        Args:
            status_code: HTTP status to return to the caller.
            code: Machine-readable identifier for the failure.
            message: Public explanation safe to return to the caller.
        """
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def api_error_handler(request: Request, error: ApiError) -> JSONResponse:
    """Convert an expected API error into the common public envelope.

    Args:
        request: Request holding the trace ID assigned by middleware.
        error: Expected failure to convert into the common error envelope.

    Returns:
        JSONResponse: Error response containing code, message, and trace ID.
    """
    trace_id = str(getattr(request.state, "trace_id", ""))
    logger.info(
        "Returning expected API error",
        extra={"trace_id": trace_id, "status_code": error.status_code, "error_code": error.code},
    )
    return JSONResponse(
        status_code=error.status_code,
        content={"code": error.code, "message": error.message, "traceId": trace_id},
    )
