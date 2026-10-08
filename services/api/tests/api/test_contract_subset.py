import json
from pathlib import Path

from pydantic import BaseModel

from monetae.api.main import create_app
from monetae.api.schemas.auth import (
    ActionResult,
    AuthenticatedSession,
    CurrentUser,
    GoogleLogin,
    PasswordLogin,
    Session,
    SessionPage,
    UserPreferences,
    UserUpdate,
)
from monetae.config import Settings

# json.loads and FastAPI OpenAPI expose untyped JSON at this contract boundary.
CONTRACT = Path(__file__).resolve().parents[4] / "docs/api/openapi.json"


def test_mounted_operations_security_responses_and_csrf() -> None:
    contract = json.loads(CONTRACT.read_text())
    actual = create_app(Settings(environment="test")).openapi()
    count = 0
    for path, methods in actual["paths"].items():
        assert path in contract["paths"]
        for method, operation in methods.items():
            expected = contract["paths"][path][method]
            assert operation["operationId"] == expected["operationId"]
            assert operation.get("security", []) == expected.get(
                "security", contract.get("security", [])
            )
            assert set(expected["responses"]) <= set(operation["responses"])
            if method in {"post", "put", "patch", "delete"}:
                assert any(
                    p.get("name") == "X-CSRF-Token" and p["in"] == "header" and p["required"]
                    for p in operation["parameters"]
                )
            count += 1
    assert count == 9


def test_schema_properties_mirror_contract() -> None:
    schemas = json.loads(CONTRACT.read_text())["components"]["schemas"]
    models: list[type[BaseModel]] = [
        PasswordLogin,
        GoogleLogin,
        AuthenticatedSession,
        CurrentUser,
        UserUpdate,
        UserPreferences,
        Session,
        SessionPage,
        ActionResult,
    ]
    for model in models:
        actual = model.model_json_schema()
        expected = schemas[model.__name__]
        assert set(actual["properties"]) == set(expected["properties"])
        assert actual["additionalProperties"] is False
        assert set(actual.get("required", [])) == set(expected["required"])


def test_openapi_references_resolve() -> None:
    actual = create_app(Settings(environment="test")).openapi()

    def walk(value: object) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str):
                assert ref.startswith("#/")
                target = actual
                for segment in ref[2:].split("/"):
                    target = target[segment]
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(actual)
