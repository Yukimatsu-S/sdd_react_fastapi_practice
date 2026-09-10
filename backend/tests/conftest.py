"""Opt-in shared MySQL fixtures; unit tests do not request a DB connection."""

from uuid import uuid4

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import load_settings


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
