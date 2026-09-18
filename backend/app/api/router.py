"""Shared API router and lazy request-Session dependency."""

from collections.abc import Iterator

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session, sessionmaker

from app.config import load_settings
from app.infrastructure.database import build_engine, get_session

api_router = APIRouter(prefix="/api/v1")


def get_request_session(request: Request) -> Iterator[Session]:
    """Yield one request Session, creating the app's factory on first use.

    Args:
        request: Request whose application stores the reusable Session factory.

    Yields:
        Session: One fresh Session closed after the request finishes.
    """
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        engine = build_engine(load_settings())
        session_factory = sessionmaker(bind=engine)
        request.app.state.session_factory = session_factory

    yield from get_session(session_factory)
