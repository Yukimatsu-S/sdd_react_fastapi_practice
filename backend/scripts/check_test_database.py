"""Read-only setup check using the test database URL in .env.example."""

from pathlib import Path

import pymysql
from sqlalchemy.engine import make_url

ENV_EXAMPLE_PATH = Path(__file__).resolve().parents[1] / ".env.example"


def read_test_database_url() -> str:
    """Read the explicit test setting, without loading the application URL."""
    for line in ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        name, value = line.split("=", maxsplit=1)
        if name == "MONDEL_TEST_DATABASE_URL":
            return value

    raise ValueError("MONDEL_TEST_DATABASE_URL is missing from .env.example")


def main() -> None:
    # Parse the URL first. No connection is made by make_url().
    url = make_url(read_test_database_url())
    if (url.drivername, url.host, url.port, url.database) != (
        "mysql+pymysql",
        "127.0.0.1",
        3307,
        "mondel_test",
    ):
        raise ValueError("Expected the local test database at 127.0.0.1:3307/mondel_test")

    # Connect from the Mac through the published Docker port.
    connection = pymysql.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        database=url.database,
        connect_timeout=5,
        read_timeout=5,
        write_timeout=5,
    )
    try:
        # A cursor sends SQL and receives its result; this query writes no data.
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1, DATABASE(), VERSION()")
            result = cursor.fetchone()

        if result != (1, "mondel_test", "8.0.46"):
            raise RuntimeError(f"Unexpected database response: {result!r}")
        print(f"PASS: {result}")
    finally:
        # Close the connection even if the query or result check fails.
        connection.close()


if __name__ == "__main__":
    main()
