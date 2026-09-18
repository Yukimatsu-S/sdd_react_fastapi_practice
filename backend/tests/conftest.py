"""Opt-in shared MySQL fixtures; unit tests do not request a DB connection."""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import load_settings

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DROP_ORDER = (
    "evolution_step_history",
    "dataset_input",
    "best_step_metric",
    "run_parameter",
    "run_snapshot",
    "evolution_step",
    "run_reference",
    "lineage_mutation_guard",
    "alembic_version",
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Provide an HTTP client for one newly created application.

    Yields:
        TestClient: Isolated client that returns server errors as HTTP responses.
    """
    from main import create_app

    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def database_settings():
    settings = load_settings(testing=True)
    url = make_url(settings.database_url)
    if (url.drivername, url.host, url.port, url.database) != (
        "mysql+pymysql", "127.0.0.1", 3307, "mondel_test"
    ):
        pytest.fail("DB fixtures only permit the local test database at 127.0.0.1:3307/mondel_test")
    return settings


@pytest.fixture(scope="session")
def database_engine(database_settings):
    # Standard SQLAlchemy setup, independent of the application's T011 helpers.
    engine = create_engine(
        database_settings.database_url,
        connect_args={"connect_timeout": 5, "read_timeout": 5, "write_timeout": 5},
    )
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT DATABASE()")) == "mondel_test"
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def migrated_schema(
    database_engine: Engine,
) -> Callable[[], AbstractContextManager[Connection]]:
    """Provide an empty migration-created schema for one integration test.

    Args:
        database_engine: Engine limited to the dedicated local test database.

    Returns:
        Callable[[], AbstractContextManager[Connection]]: Context factory that
            applies the initial migration and removes only its own tables.
    """
    @contextmanager
    def apply_initial_migration() -> Iterator[Connection]:
        """Apply the initial revision and remove its tables after the test.

        Yields:
            Connection: Connection against the temporary migrated schema.

        Raises:
            AssertionError: Existing migration tables would be overwritten.
        """
        with database_engine.connect() as connection:
            existing_tables = set(inspect(connection).get_table_names())
            existing_views = set(inspect(connection).get_view_names())
            conflicts = (existing_tables | existing_views).intersection(SCHEMA_DROP_ORDER)
            assert not conflicts, f"Migration tables already exist: {sorted(conflicts)}"

            config = Config(str(BACKEND_ROOT / "alembic.ini"))
            config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
            config.attributes["connection"] = connection
            try:
                command.upgrade(config, "head")
                connection.commit()
                yield connection
            finally:
                connection.rollback()
                remaining_tables = set(inspect(connection).get_table_names())
                for table_name in SCHEMA_DROP_ORDER:
                    if table_name in remaining_tables and table_name not in existing_tables:
                        connection.execute(text(f"DROP TABLE `{table_name}`"))
                connection.commit()

    return apply_initial_migration


@pytest.fixture
def probe_table(database_engine):
    metadata = MetaData()
    table = Table(
        "t010_probe_" + uuid4().hex,
        metadata,
        Column("id", Integer, primary_key=True),
        mysql_engine="InnoDB",
    )
    # CREATE/DROP are outside the transaction being tested. Never drop other tables.
    table.create(database_engine, checkfirst=False)
    try:
        yield table
    finally:
        table.drop(database_engine, checkfirst=False)


@pytest.fixture
def database_session(database_engine, probe_table):
    # Explicit dependency ensures Session closes before its probe table is dropped.
    with Session(database_engine) as session:
        yield session


@pytest.fixture
def request_session_factory(database_engine, probe_table):
    sessions = []
    factory = sessionmaker(bind=database_engine)

    def create_session():
        session = factory()
        sessions.append(session)
        return session

    try:
        yield create_session
    finally:
        # Safety cleanup even when the application's unfinished lifecycle fails.
        for session in sessions:
            session.close()
