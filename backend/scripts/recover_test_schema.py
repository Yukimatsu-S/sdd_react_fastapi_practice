"""Explicit recovery of the Compose mysql-test database; never runs at import."""

import argparse
import hashlib
import json
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
BACKUP_ROOT = ROOT / "backend/.local/schema-recovery"
TABLES = (
    "evolution_step_history", "dataset_input", "best_step_metric", "run_parameter",
    "run_snapshot", "evolution_step", "run_reference", "lineage_mutation_guard",
    "alembic_version",
)
CONFIRM_RESET = "DELETE mondel_test schema"
CONFIRM_RESTORE = "RESTORE mondel_test backup"


def run_client(
    program: str,
    arguments: list[str],
    *,
    input_data: bytes | None = None,
) -> bytes:
    """Use only the repository's dedicated Compose service and its credentials."""
    command = [
        "docker", "compose", "-f", str(ROOT / "docker-compose.test.yml"),
        "exec", "-T", "mysql-test", "sh", "-c",
        (
            'test "$MYSQL_DATABASE" = mondel_test && '
            'test "$MYSQL_USER" = mondel_test && '
            'export MYSQL_PWD="$MYSQL_PASSWORD" && exec "$@"'
        ),
        "recovery-client", program, "--user=mondel_test", *arguments,
    ]
    result = subprocess.run(command, input=input_data, capture_output=True, timeout=120, check=False)
    if result.returncode:
        client_error = result.stderr.decode(errors="replace")
        raise RuntimeError(
            "MySQL client failed; no automatic retry. Check container health and "
            f"inspect the database before continuing. Client error: {client_error}"
        )
    return result.stdout


def execute_sql(statement: str) -> str:
    return run_client("mysql", [
        "--batch", "--skip-column-names", "mondel_test", "--execute", statement,
    ]).decode().strip()


def inspect_database() -> dict[str, int]:
    if execute_sql("SELECT DATABASE()") != "mondel_test":
        raise ValueError("Expected dedicated database mondel_test")
    listing = execute_sql("SHOW FULL TABLES")
    tables: dict[str, int] = {}
    for line in listing.splitlines():
        name, kind = line.split("\t")
        if name not in TABLES or kind != "BASE TABLE":
            raise ValueError(f"Unexpected object {name!r}; preserve it and stop")
        tables[name] = 0
    # Dumps/restores below deliberately support ordinary InnoDB tables only.
    checks = [
        "SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()",
        "SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE()",
        "SELECT COUNT(*) FROM information_schema.EVENTS WHERE EVENT_SCHEMA=DATABASE()",
        "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND ENGINE <> 'InnoDB'",
        "SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE WHERE REFERENCED_TABLE_SCHEMA=DATABASE() AND TABLE_SCHEMA <> DATABASE()",
    ]
    if any(execute_sql(query) != "0" for query in checks):
        raise ValueError("Unsupported objects or cross-database references; preserve DB and stop")
    for name in tables:
        tables[name] = int(execute_sql(f"SELECT COUNT(*) FROM `{name}`"))
    print("Target: Compose mysql-test / mondel_test")
    print(json.dumps(tables, indent=2))
    if "alembic_version" in tables:
        print("Migration revision:", execute_sql("SELECT version_num FROM alembic_version"))
    return tables


def create_backup(backup_root: Path, state: dict[str, int]) -> Path:
    label = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    directory = Path(backup_root) / label
    directory.mkdir(parents=True, mode=0o700)
    dump = run_client("mysqldump", [
        "--single-transaction", "--no-tablespaces", "--set-gtid-purged=OFF",
        "--hex-blob", "--skip-triggers", "--skip-add-drop-table", "mondel_test",
    ])
    if not dump.strip():
        raise RuntimeError("Empty backup; deletion is forbidden")
    with (directory / "schema.sql").open("xb") as output:
        output.write(dump)
    manifest = {"database": "mondel_test", "tables": state,
                "sha256": hashlib.sha256(dump).hexdigest()}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("Backup:", directory)
    print("Restore command (run in backend): uv run python scripts/recover_test_schema.py restore --backup-dir",
          shlex.quote(str(directory)))
    return directory


def read_backup(backup_directory: Path) -> tuple[bytes, dict[str, int]]:
    directory = Path(backup_directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    dump = (directory / "schema.sql").read_bytes()
    if manifest.get("database") != "mondel_test" or not set(manifest["tables"]) <= set(TABLES):
        raise ValueError("Backup does not belong to this test schema")
    if hashlib.sha256(dump).hexdigest() != manifest.get("sha256"):
        raise ValueError("Backup checksum mismatch; do not restore")
    return dump, manifest["tables"]


def reset_schema(backup_root: Path) -> None:
    state = inspect_database()
    if not state:
        print("Already empty; nothing deleted")
        return
    if input(f"Stop all other DB users. Type {CONFIRM_RESET!r}: ") != CONFIRM_RESET:
        raise ValueError("Reset confirmation did not match; no changes made")
    create_backup(backup_root, state)
    # Keep FK checks enabled: an unexpected dependency stops deletion safely.
    for name in TABLES:
        if name in state:
            execute_sql(f"DROP TABLE `{name}`")
    if inspect_database():
        raise RuntimeError("Tables remain; inspect before retrying")
    print("Reset complete. Tables/data removed; backup retained for restoration.")


def restore_schema(backup_directory: Path) -> None:
    if inspect_database():
        raise ValueError("Restore requires an empty database; no overwrite allowed")
    dump, expected = read_backup(backup_directory)
    if input(f"Use only your own trusted backup. Type {CONFIRM_RESTORE!r}: ") != CONFIRM_RESTORE:
        raise ValueError("Restore confirmation did not match; no changes made")
    run_client("mysql", ["mondel_test"], input_data=dump)
    if inspect_database() != expected:
        raise RuntimeError("Restored table/count verification failed; preserve backup and inspect")
    print("Restore complete: table names and row counts match the backup manifest.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inspect", "backup", "reset", "restore"])
    parser.add_argument("--backup-dir", type=Path)
    args = parser.parse_args()
    if args.action == "inspect":
        inspect_database()
    elif args.action == "backup":
        create_backup(BACKUP_ROOT, inspect_database())
    elif args.action == "reset":
        reset_schema(BACKUP_ROOT)
    else:
        if args.backup_dir is None:
            parser.error("restore requires --backup-dir")
        restore_schema(args.backup_dir)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        raise SystemExit(f"STOP: {error}") from None
