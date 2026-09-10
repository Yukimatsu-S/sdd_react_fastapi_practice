"""T010 importable interfaces only; database lifecycle behavior belongs to T011."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import Settings


def build_engine(settings: Settings) -> Engine | None:
    """Unimplemented: T011 will construct the synchronous Engine."""
    return None


def get_session(session_factory: Callable[[], Session]) -> Iterator[Session | None]:
    """Unimplemented: expose a generator without creating/closing a Session."""
    yield None


@contextmanager
def transaction_scope(session: Session) -> Iterator[Session]:
    """T010 pass-through scaffold: deliberately no begin, commit, or rollback."""
    yield session
