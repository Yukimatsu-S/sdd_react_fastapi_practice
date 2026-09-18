"""Public error types and response conversion for the API boundary."""

import logging

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
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
    trace_id = _trace_id(request)
    logger.info(
        "Returning expected API error",
        extra={"trace_id": trace_id, "status_code": error.status_code, "error_code": error.code},
    )
    return _error_response(request, error.status_code, error.code, error.message)


def request_validation_error_handler(
    request: Request, error: RequestValidationError,
) -> JSONResponse:
    """Return the public envelope for FastAPI request validation failures.

    Args:
        request: Request holding the trace ID assigned by middleware.
        error: Validation failure raised before a path operation runs.

    Returns:
        JSONResponse: Safe validation-error response with the request trace ID.
    """
    logger.info("Returning request validation error", extra={"trace_id": _trace_id(request)})
    return _error_response(request, 422, "validation_error", "Request validation failed.")


def http_exception_handler(
    request: Request, error: StarletteHTTPException,
) -> JSONResponse:
    """Return the public envelope for HTTP routing errors.

    Args:
        request: Request holding the trace ID assigned by middleware.
        error: HTTP exception raised by FastAPI or Starlette routing.

    Returns:
        JSONResponse: HTTP error response with the request trace ID.
    """
    code = "not_found" if error.status_code == 404 else "http_error"
    message = str(error.detail)
    logger.info(
        "Returning HTTP error",
        extra={"trace_id": _trace_id(request), "status_code": error.status_code, "error_code": code},
    )
    return _error_response(request, error.status_code, code, message)


def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
    """Hide unexpected exception details behind a traceable public response.

    Args:
        request: Request holding the trace ID assigned by middleware.
        error: Unexpected exception that must not expose internal details.

    Returns:
        JSONResponse: Generic internal-error response with the request trace ID.
    """
    logger.exception("Returning unexpected API error", extra={"trace_id": _trace_id(request)})
    return _error_response(request, 500, "internal_error", "An unexpected error occurred.")


def _trace_id(request: Request) -> str:
    """Read the trace ID assigned by middleware without exposing request state.

    Args:
        request: Request that may carry a trace ID in its state.

    Returns:
        str: Trace ID string, or an empty string before middleware is registered.
    """
    return str(getattr(request.state, "trace_id", ""))


def _error_response(
    request: Request, status_code: int, code: str, message: str,
) -> JSONResponse:
    """Create one response conforming to the project's common error contract.

    Args:
        request: Request holding the trace ID assigned by middleware.
        status_code: HTTP status to return.
        code: Machine-readable public error code.
        message: Public error message safe for the caller.

    Returns:
        JSONResponse: JSON object containing code, message, and trace ID.
    """
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "traceId": _trace_id(request)},
    )
