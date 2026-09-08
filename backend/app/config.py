"""Configuration interface; validation will be implemented in T009."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    mlflow_tracking_uri: str


def load_settings(*, testing: bool = False) -> Settings | None:
    """T008 scaffold: no environment loading, validation, or connections yet."""
    return None
