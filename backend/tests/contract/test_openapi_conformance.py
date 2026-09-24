"""Compare every implemented HTTP operation with the versioned OpenAPI contract."""

from pathlib import Path
from typing import Any

import yaml

from main import create_app

CONTRACT_PATH = Path(__file__).resolve().parents[3] / "specs/001-experiment-evolution/contracts/openapi.yaml"
HTTP_METHODS = {"get", "post", "patch", "put", "delete"}


def test_runtime_openapi_covers_every_documented_operation_and_response() -> None:
    """Keep generated API paths, methods, and documented response codes in sync.

    The checked-in contract uses paths relative to ``/api/v1``. FastAPI emits
    absolute application paths, so the test adds that version prefix only while
    looking up the generated operation.
    """
    contract_paths = _contract_paths()
    runtime_paths = create_app().openapi()["paths"]

    for contract_path, contract_path_item in contract_paths.items():
        runtime_path = f"/api/v1{contract_path}"
        assert runtime_path in runtime_paths, f"Missing runtime path: {runtime_path}"
        for method, contract_operation in contract_path_item.items():
            if method not in HTTP_METHODS:
                continue
            assert method in runtime_paths[runtime_path], (
                f"Missing {method.upper()} operation: {runtime_path}"
            )
            expected_codes = set(contract_operation["responses"])
            actual_codes = set(runtime_paths[runtime_path][method]["responses"])
            assert expected_codes.issubset(actual_codes), (
                f"{method.upper()} {runtime_path} is missing response codes: "
                f"{sorted(expected_codes.difference(actual_codes))}"
            )


def _contract_paths() -> dict[str, dict[str, Any]]:
    """Load only the path-operation mapping from the checked-in contract.

    Returns:
        dict[str, dict[str, Any]]: Contract path strings and their operations.
    """
    document = yaml.safe_load(CONTRACT_PATH.read_text())
    return document["paths"]
