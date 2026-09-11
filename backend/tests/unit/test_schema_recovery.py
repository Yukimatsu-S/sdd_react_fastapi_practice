"""Recovery safety tests use fakes only; no Docker or database writes."""

import builtins
import json

import pytest

from scripts import recover_test_schema as recovery


def test_reset_cancellation_does_not_backup_or_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, "inspect_database", lambda: {"run_reference": 2})
    monkeypatch.setattr(builtins, "input", lambda prompt: "no")
    monkeypatch.setattr(recovery, "create_backup", lambda *args: pytest.fail("No backup expected"))
    monkeypatch.setattr(recovery, "execute_sql", lambda sql: pytest.fail("No deletion expected"))
    with pytest.raises(ValueError, match="confirmation"):
        recovery.reset_schema(tmp_path)


def test_backup_failure_prevents_deletion(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, "inspect_database", lambda: {"run_reference": 2})
    monkeypatch.setattr(builtins, "input", lambda prompt: recovery.CONFIRM_RESET)

    def failed_backup(*args):
        raise RuntimeError("backup failed")

    monkeypatch.setattr(recovery, "create_backup", failed_backup)
    monkeypatch.setattr(recovery, "execute_sql", lambda sql: pytest.fail("No deletion expected"))
    with pytest.raises(RuntimeError, match="backup failed"):
        recovery.reset_schema(tmp_path)


def test_reset_backs_up_before_deleting_in_dependency_order(monkeypatch, tmp_path):
    states = iter([{"run_reference": 1, "evolution_step": 1}, {}])
    monkeypatch.setattr(recovery, "inspect_database", lambda: next(states))
    monkeypatch.setattr(builtins, "input", lambda prompt: recovery.CONFIRM_RESET)
    events = []

    def backup(root, state):
        events.append("backup")
        return tmp_path

    monkeypatch.setattr(recovery, "create_backup", backup)
    monkeypatch.setattr(recovery, "execute_sql", lambda sql: events.append(sql))
    recovery.reset_schema(tmp_path)
    assert events == [
        "backup", "DROP TABLE `evolution_step`", "DROP TABLE `run_reference`",
    ]


def test_restore_refuses_nonempty_database(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, "inspect_database", lambda: {"run_reference": 1})
    monkeypatch.setattr(recovery, "read_backup", lambda path: pytest.fail("Must stop first"))
    with pytest.raises(ValueError, match="empty"):
        recovery.restore_schema(tmp_path)


def test_unknown_table_prevents_reset(monkeypatch, tmp_path):
    queries = []

    def query(sql):
        queries.append(sql)
        return "mondel_test" if sql == "SELECT DATABASE()" else "important_data\tBASE TABLE"

    monkeypatch.setattr(recovery, "execute_sql", query)
    with pytest.raises(ValueError, match="Unexpected object"):
        recovery.reset_schema(tmp_path)
    assert not any("DROP" in sql for sql in queries)


def test_wrong_database_is_rejected(monkeypatch):
    monkeypatch.setattr(recovery, "execute_sql", lambda sql: "mondel")
    with pytest.raises(ValueError, match="dedicated database"):
        recovery.inspect_database()


def test_backup_round_trip_and_tampering(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, "run_client", lambda *args: b"test dump bytes")
    directory = recovery.create_backup(tmp_path, {"run_reference": 2})
    assert recovery.read_backup(directory) == (b"test dump bytes", {"run_reference": 2})
    (directory / "schema.sql").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        recovery.read_backup(directory)


def test_empty_dump_is_not_a_backup(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, "run_client", lambda *args: b"")
    with pytest.raises(RuntimeError, match="Empty backup"):
        recovery.create_backup(tmp_path, {})


def test_restore_cancellation_does_not_write(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, "inspect_database", dict)
    monkeypatch.setattr(recovery, "read_backup", lambda path: (b"dump", {}))
    monkeypatch.setattr(builtins, "input", lambda prompt: "no")
    monkeypatch.setattr(recovery, "run_client", lambda *args, **kwargs: pytest.fail("No writes"))
    with pytest.raises(ValueError, match="confirmation"):
        recovery.restore_schema(tmp_path)


def test_restore_verifies_table_counts(monkeypatch, tmp_path):
    states = iter([{}, {"run_reference": 2}])
    monkeypatch.setattr(recovery, "inspect_database", lambda: next(states))
    monkeypatch.setattr(recovery, "read_backup", lambda path: (b"dump", {"run_reference": 2}))
    monkeypatch.setattr(builtins, "input", lambda prompt: recovery.CONFIRM_RESTORE)
    writes = []
    monkeypatch.setattr(recovery, "run_client", lambda *args, **kwargs: writes.append(kwargs))
    recovery.restore_schema(tmp_path)
    assert writes == [{"input_data": b"dump"}]


def test_client_targets_only_compose_test_service(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return recovery.subprocess.CompletedProcess(command, 0, b"ok", b"")

    monkeypatch.setattr(recovery.subprocess, "run", run)
    assert recovery.execute_sql("SELECT DATABASE()") == "ok"
    command, options = calls[0]
    assert command[:4] == ["docker", "compose", "-f", str(recovery.ROOT / "docker-compose.test.yml")]
    assert command[4:8] == ["exec", "-T", "mysql-test", "sh"]
    assert "mondel_test" in command
    assert "MYSQL_DATABASE" in command[9]
    assert options["timeout"] == 120


def test_foreign_backup_is_rejected(tmp_path):
    (tmp_path / "schema.sql").write_bytes(b"dump")
    (tmp_path / "manifest.json").write_text(json.dumps({"database": "mondel"}))
    with pytest.raises(ValueError, match="does not belong"):
        recovery.read_backup(tmp_path)
