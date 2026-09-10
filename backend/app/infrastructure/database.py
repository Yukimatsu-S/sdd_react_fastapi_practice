"""Synchronous connection, Session, and transaction lifecycle helpers."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import Settings


def build_engine(settings: Settings) -> Engine:
    """Build connection management from explicit settings; connect lazily."""
    return create_engine(
        settings.database_url,
        connect_args={"connect_timeout": 5, "read_timeout": 5, "write_timeout": 5},
    )


def get_session(session_factory: Callable[[], Session]) -> Iterator[Session]:
    """Yield one fresh Session and close it without automatically committing."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def transaction_scope(session: Session) -> Iterator[Session]:
    """Own one transaction, not the Session; reject an already active transaction."""
    # Begin outside try: failure to start must not roll back a caller's transaction.
    session.begin()
    try:
        yield session
        session.commit()
    except BaseException:
        # Also clean up interruptions/generator closure, then propagate the error.
        session.rollback()
        raise
