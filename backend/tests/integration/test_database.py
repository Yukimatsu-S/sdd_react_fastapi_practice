"""T010: real MySQL probes for the application's unimplemented DB boundary."""

import inspect
from contextlib import closing

import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.database import build_engine, get_session, transaction_scope


def read_ids(engine, table):
    """Read from a separate connection/transaction, not the writer's Session."""
    with engine.connect() as connection:
        return list(connection.scalars(select(table.c.id).order_by(table.c.id)))


def test_fixture_can_reach_dedicated_mysql(database_engine, probe_table):
    with database_engine.connect() as connection:
        assert connection.scalar(text("SELECT DATABASE()")) == "mondel_test"
    assert read_ids(database_engine, probe_table) == []


def test_build_engine_uses_explicit_test_settings(database_settings):
    engine = build_engine(database_settings)
    try:
        assert isinstance(engine, Engine), "build_engine must return a synchronous Engine"
        assert engine.url.database == "mondel_test"
        assert engine.url.host == "127.0.0.1"
        assert engine.url.port == 3307
        assert engine.dialect.driver == "pymysql"
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT DATABASE()")) == "mondel_test"
    finally:
        if isinstance(engine, Engine):
            engine.dispose()


def test_request_session_dependency_is_synchronous():
    assert not inspect.iscoroutinefunction(get_session)
    assert not inspect.isasyncgenfunction(get_session)
    assert inspect.isgeneratorfunction(get_session)


def test_request_invocations_get_distinct_sessions(request_session_factory):
    with (
        closing(get_session(request_session_factory)) as first_request,
        closing(get_session(request_session_factory)) as second_request,
    ):
        first = next(first_request)
        second = next(second_request)
        assert isinstance(first, Session), "Dependency must yield a Session"
        assert isinstance(second, Session), "Dependency must yield a Session"
        assert first is not second


@pytest.mark.parametrize("end_with_error", [False, True])
def test_request_cleanup_closes_without_committing(
    request_session_factory, database_engine, probe_table, monkeypatch, end_with_error
):
    with closing(get_session(request_session_factory)) as request:
        session = next(request)
        assert isinstance(session, Session), "Dependency must yield a Session"
        close_calls = []
        original_close = session.close

        def record_close():
            close_calls.append(True)
            original_close()

        monkeypatch.setattr(session, "close", record_close)
        session.execute(insert(probe_table).values(id=1))
        assert read_ids(database_engine, probe_table) == []

        if end_with_error:
            error = RuntimeError("request failed")
            with pytest.raises(RuntimeError) as caught:
                request.throw(error)
            assert caught.value is error
        else:
            with pytest.raises(StopIteration):
                next(request)

        assert close_calls == [True]
        assert not session.in_transaction()
        assert read_ids(database_engine, probe_table) == []


def test_transaction_commits_all_rows(database_session, database_engine, probe_table):
    with transaction_scope(database_session) as session:
        assert session is database_session
        session.execute(insert(probe_table).values(id=1))
        session.execute(insert(probe_table).values(id=2))
        assert read_ids(database_engine, probe_table) == []

    assert read_ids(database_engine, probe_table) == [1, 2]
    assert not database_session.in_transaction()


@pytest.mark.parametrize("failure", ["application", "duplicate_key"])
def test_transaction_rolls_back_all_rows(
    database_session, database_engine, probe_table, failure
):
    error = RuntimeError("second operation failed")
    expected_error = RuntimeError if failure == "application" else IntegrityError
    with (
        pytest.raises(expected_error) as caught,
        transaction_scope(database_session) as session,
    ):
        session.execute(insert(probe_table).values(id=1))
        if failure == "duplicate_key":
            session.execute(insert(probe_table).values(id=1))
        else:
            raise error

    if failure == "application":
        assert caught.value is error
    # A different connection seeing no rows alone would not prove rollback:
    # an unfinished transaction also hides its changes from that connection.
    assert not database_session.in_transaction(), "Failed transaction must be ended"
    assert read_ids(database_engine, probe_table) == []
    assert list(database_session.scalars(select(probe_table.c.id))) == []


def test_commit_failure_rolls_back_and_propagates(
    database_session, database_engine, probe_table, monkeypatch
):
    error = RuntimeError("commit failed")

    def fail_commit():
        raise error

    monkeypatch.setattr(database_session, "commit", fail_commit)
    with (
        pytest.raises(RuntimeError) as caught,
        transaction_scope(database_session) as session,
    ):
        session.execute(insert(probe_table).values(id=1))

    assert caught.value is error
    assert not database_session.in_transaction()
    assert read_ids(database_engine, probe_table) == []
