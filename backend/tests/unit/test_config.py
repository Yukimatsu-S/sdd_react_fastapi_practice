"""T008: configuration behavior, without connecting to MySQL or MLflow."""

import pytest

from app.config import (
    Settings,
    load_settings,
    validate_database_url,
    validate_mlflow_uri,
)

APPLICATION_URL = "mysql+pymysql://example:example@127.0.0.1:3306/mondel"
TEST_URL = "mysql+pymysql://example:example@127.0.0.1:3307/mondel_test"
MLFLOW_URI = "http://127.0.0.1:5000"


@pytest.fixture(autouse=True)
def configuration_environment(monkeypatch, tmp_path):
    """Each case starts with known values and no developer-local .env file."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MONDEL_DATABASE_URL", APPLICATION_URL)
    monkeypatch.setenv("MONDEL_TEST_DATABASE_URL", TEST_URL)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", MLFLOW_URI)


@pytest.mark.parametrize("testing, expected_url", [(False, APPLICATION_URL), (True, TEST_URL)])
def test_explicit_mode_selects_database(testing, expected_url):
    settings = load_settings(testing=testing)

    assert isinstance(settings, Settings), "Validated Settings must be returned"
    assert settings.database_url == expected_url
    assert settings.mlflow_tracking_uri == MLFLOW_URI


def test_normal_mode_does_not_require_test_database(monkeypatch):
    monkeypatch.delenv("MONDEL_TEST_DATABASE_URL")

    settings = load_settings(testing=False)

    assert isinstance(settings, Settings), "Normal settings must be returned"
    assert settings.database_url == APPLICATION_URL


def test_test_mode_does_not_require_application_database(monkeypatch):
    monkeypatch.delenv("MONDEL_DATABASE_URL")

    settings = load_settings(testing=True)

    assert isinstance(settings, Settings), "Test settings must be returned"
    assert settings.database_url == TEST_URL


@pytest.mark.parametrize("testing, variable", [
    (False, "MONDEL_DATABASE_URL"),
    (True, "MONDEL_TEST_DATABASE_URL"),
])
def test_selected_database_is_required(monkeypatch, testing, variable):
    monkeypatch.delenv(variable)

    with pytest.raises(ValueError, match=variable):
        load_settings(testing=testing)


@pytest.mark.parametrize("testing, variable", [
    (False, "MONDEL_DATABASE_URL"),
    (True, "MONDEL_TEST_DATABASE_URL"),
])
@pytest.mark.parametrize("invalid_url", [
    "",
    "   ",
    "こんにちは",
    "sqlite:///mondel.db",
    "mysql+pymysql://example:example@:3307/mondel_test",
    "mysql+pymysql://example:example@127.0.0.1:3307/",
    "mysql+pymysql://example:example@127.0.0.1:abc/mondel_test",
    "mysql+pymysql://example:example@127.0.0.1:70000/mondel_test",
])
def test_invalid_selected_database_is_rejected(monkeypatch, testing, variable, invalid_url):
    monkeypatch.setenv(variable, invalid_url)

    with pytest.raises(ValueError, match=variable):
        load_settings(testing=testing)


def test_test_database_cannot_equal_application_database(monkeypatch):
    monkeypatch.setenv("MONDEL_TEST_DATABASE_URL", APPLICATION_URL)

    with pytest.raises(ValueError, match="MONDEL_TEST_DATABASE_URL"):
        load_settings(testing=True)


def test_mlflow_tracking_uri_is_required(monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI")

    with pytest.raises(ValueError, match="MLFLOW_TRACKING_URI"):
        load_settings(testing=True)


@pytest.mark.parametrize("invalid_uri", ["", "   ", "こんにちは", "file:///tmp/mlruns", "http://"])
def test_invalid_mlflow_tracking_uri_is_rejected(monkeypatch, invalid_uri):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", invalid_uri)

    with pytest.raises(ValueError, match="MLFLOW_TRACKING_URI"):
        load_settings(testing=True)


def test_https_mlflow_server_is_supported(monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "https://mlflow.example.test")

    settings = load_settings(testing=True)

    assert isinstance(settings, Settings), "Validated Settings must be returned"
    assert settings.mlflow_tracking_uri == "https://mlflow.example.test"


@pytest.mark.parametrize("testing, variable", [
    (False, "MONDEL_DATABASE_URL"),
    (True, "MONDEL_TEST_DATABASE_URL"),
    (True, "MLFLOW_TRACKING_URI"),
])
@pytest.mark.parametrize("whitespace", [" ", "\t", "\n", "\u3000"])
@pytest.mark.parametrize("position", ["leading", "trailing", "host", "path"])
def test_raw_whitespace_is_rejected(monkeypatch, testing, variable, whitespace, position):
    if variable == "MLFLOW_TRACKING_URI":
        url = "http://mlflow.example.test/tracking"
    else:
        url = "mysql+pymysql://example:example@db.example.test/mondel"
    if position == "leading":
        url = whitespace + url
    elif position == "trailing":
        url = url + whitespace
    elif position == "host":
        url = url.replace(".example", whitespace + ".example")
    else:
        url = url + whitespace + "suffix"
    monkeypatch.setenv(variable, url)

    with pytest.raises(ValueError, match=variable):
        load_settings(testing=testing)


@pytest.mark.parametrize("kind", ["database", "mlflow"])
def test_whitespace_is_rejected_before_parser_is_called(monkeypatch, kind):
    def unexpected_parser_call(value):
        pytest.fail("Whitespace must be rejected before calling the URL parser")

    if kind == "database":
        monkeypatch.setattr("app.config.make_url", unexpected_parser_call)
        with pytest.raises(ValueError, match="MONDEL_TEST_DATABASE_URL"):
            validate_database_url(TEST_URL + " ", "MONDEL_TEST_DATABASE_URL")
    else:
        monkeypatch.setattr("app.config.urlsplit", unexpected_parser_call)
        with pytest.raises(ValueError, match="MLFLOW_TRACKING_URI"):
            validate_mlflow_uri(MLFLOW_URI + " ")


def test_percent_encoded_values_are_not_decoded_or_rewritten(monkeypatch):
    database_url = "mysql+pymysql://example:pass%20word@db.example.test/mondel"
    mlflow_uri = "https://mlflow.example.test/tracking%20service"
    monkeypatch.setenv("MONDEL_TEST_DATABASE_URL", database_url)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", mlflow_uri)

    settings = load_settings(testing=True)

    assert settings.database_url == database_url
    assert settings.mlflow_tracking_uri == mlflow_uri
