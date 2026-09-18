"""FastAPI dependencies shared by versioned route modules."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker

from app.config import load_settings
from app.infrastructure.database import build_engine, get_session


def get_request_session(request: Request) -> Iterator[Session]:
    """Yield one request Session, creating the app factory on first use.

    Args:
        request: Request whose application holds the reusable Session factory.

    Yields:
        Session: One fresh Session closed after the request finishes.
    """
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        engine = build_engine(load_settings())
        session_factory = sessionmaker(bind=engine)
        request.app.state.session_factory = session_factory

    yield from get_session(session_factory)
