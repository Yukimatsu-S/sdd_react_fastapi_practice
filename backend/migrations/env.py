"""Connect Alembic to Mondel metadata and an explicitly selected database."""

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from app.config import read_required_environment, validate_database_url
from app.infrastructure.models import metadata


def selected_database_url() -> str:
    """Read the CLI-selected database URL without requiring MLflow settings.

    Returns:
        Validated application URL, or the explicitly selected test URL.

    Raises:
        ValueError: The database selection or required URL is invalid.
    """
    selection = context.get_x_argument(as_dictionary=True).get("database", "application")
    if selection == "application":
        variable = "MONDEL_DATABASE_URL"
    elif selection == "test":
        variable = "MONDEL_TEST_DATABASE_URL"
    else:
        raise ValueError("Use -x database=application or -x database=test")
    url = read_required_environment(variable)
    validate_database_url(url, variable)
    return url


def run_with_connection(connection: Connection) -> None:
    """Run Alembic using the caller's connection and the product definitions.

    Args:
        connection: Open connection; its lifecycle belongs to the caller.
    """
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    """Reuse an injected connection, or open and close one for CLI execution."""
    connection = context.config.attributes.get("connection")
    if connection is not None:
        run_with_connection(connection)
        return

    engine = create_engine(
        selected_database_url(),
        connect_args={"connect_timeout": 5, "read_timeout": 5, "write_timeout": 5},
    )
    try:
        with engine.connect() as connection:
            run_with_connection(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    # --sql emits SQL rather than connecting to or modifying the database.
    context.configure(
        url=selected_database_url(), target_metadata=metadata, literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    run_online()
