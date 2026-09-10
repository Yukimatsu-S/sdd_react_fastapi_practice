"""Read and validate process environment settings without opening connections."""

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


@dataclass(frozen=True)
class Settings:
    database_url: str
    mlflow_tracking_uri: str


def read_required_environment(name: str) -> str:
    """Reject missing/blank values, preserving the original non-blank value."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise ValueError(f"{name} is required")
    return value


def reject_url_whitespace(value: str, name: str) -> None:
    """Inspect the original URL before a parser can normalize its characters."""
    if any(character.isspace() for character in value):
        raise ValueError(f"{name} must not contain raw whitespace")


def validate_database_url(value: str, name: str) -> None:
    """Validate the selected MySQL URL, not the server's availability."""
    reject_url_whitespace(value, name)
    message = f"{name} must be a mysql+pymysql URL with a host, database, and valid port"
    try:
        url = make_url(value)
        valid = (
            url.drivername == "mysql+pymysql"
            and bool(url.host and url.host.strip())
            and bool(url.database and url.database.strip())
            and (url.port is None or 1 <= url.port <= 65535)
        )
    except (ArgumentError, ValueError):
        # Do not include URLs or parser errors that could contain passwords.
        raise ValueError(message) from None
    if not valid:
        raise ValueError(message)


def validate_mlflow_uri(value: str) -> None:
    """The MVP uses an external HTTP(S) Tracking Server, not a local file store."""
    reject_url_whitespace(value, "MLFLOW_TRACKING_URI")
    message = "MLFLOW_TRACKING_URI must be an HTTP(S) server URL with a host and valid port"
    try:
        url = urlsplit(value)
        valid = (
            url.scheme in ("http", "https")
            and bool(url.hostname)
            and (url.port is None or 1 <= url.port <= 65535)
        )
    except ValueError:
        raise ValueError(message) from None
    if not valid:
        raise ValueError(message)


def load_settings(*, testing: bool = False) -> Settings:
    """Select the requested mode explicitly; never fall back to a normal DB."""
    if testing:
        database_variable = "MONDEL_TEST_DATABASE_URL"
    else:
        database_variable = "MONDEL_DATABASE_URL"

    database_url = read_required_environment(database_variable)
    validate_database_url(database_url, database_variable)

    if testing and database_url == os.environ.get("MONDEL_DATABASE_URL"):
        raise ValueError("MONDEL_TEST_DATABASE_URL must differ from MONDEL_DATABASE_URL")

    mlflow_tracking_uri = read_required_environment("MLFLOW_TRACKING_URI")
    validate_mlflow_uri(mlflow_tracking_uri)

    return Settings(
        database_url=database_url,
        mlflow_tracking_uri=mlflow_tracking_uri,
    )
