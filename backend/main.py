"""Create the FastAPI application used by local execution and tests."""

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    request_validation_error_handler,
    unexpected_error_handler,
)
from app.api.router import api_router


async def add_trace_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Assign one trace ID before the application handles a request.

    Args:
        request: Incoming HTTP request that receives the trace ID.
        call_next: FastAPI function that continues request processing.

    Returns:
        Response: Response produced by the registered route or error handler.
    """
    request.state.trace_id = uuid4().hex
    return await call_next(request)


def create_app() -> FastAPI:
    """Build one isolated FastAPI application with shared HTTP boundaries.

    Returns:
        FastAPI: Application with the versioned router, error handlers, and middleware.
    """
    application = FastAPI()
    application.include_router(api_router)
    application.add_exception_handler(ApiError, api_error_handler)
    application.add_exception_handler(RequestValidationError, request_validation_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
    application.middleware("http")(add_trace_id)

    @application.get("/")
    def root() -> dict[str, str]:
        """Return the minimal service health response.

        Returns:
            dict[str, str]: Fixed response confirming that FastAPI is running.
        """
        return {"message": "Hello World"}

    return application


app = create_app()
