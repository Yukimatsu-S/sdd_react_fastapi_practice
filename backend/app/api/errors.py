"""Error types and the unfinished response boundary for T016/T017."""

from starlette.requests import Request
from starlette.responses import JSONResponse


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
    """Provide an importable scaffold; response conversion belongs to T017.

    Args:
        request: Request holding the trace ID assigned by middleware.
        error: Expected failure to convert into the common error envelope.

    Returns:
        JSONResponse: Empty placeholder, deliberately missing the contract.
    """
    return JSONResponse(content={})
