from pathlib import Path

from sqlalchemy.engine import make_url

ENV_EXAMPLE_PATH = Path(__file__).parents[2] / ".env.example"


def read_environment_example() -> dict[str, str]:
    values: dict[str, str] = {}

    for line in ENV_EXAMPLE_PATH.read_text().splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue

        name, value = stripped_line.split("=", maxsplit=1)
        values[name] = value

    return values


def test_test_database_url_is_separate_from_application_database() -> None:
    environment = read_environment_example()

    application_database_url = make_url(environment["MONDEL_DATABASE_URL"])
    test_database_url = make_url(environment["MONDEL_TEST_DATABASE_URL"])

    assert test_database_url != application_database_url
    assert test_database_url.drivername == "mysql+pymysql"
    assert test_database_url.host == "127.0.0.1"
    assert test_database_url.port == 3307
    assert test_database_url.database == "mondel_test"
