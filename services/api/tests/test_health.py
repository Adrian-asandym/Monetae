import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from monetae.api.main import create_app
from monetae.api.routers.health import Health
from monetae.config import Settings


def test_health_matches_contract(client: TestClient, application: FastAPI) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}
    assert Health.model_validate_json(response.content) == Health(status="ok")
    contract_path = Path(__file__).resolve().parents[3] / "docs/api/openapi.json"
    # json.load and FastAPI's OpenAPI expose untyped JSON at this contract boundary.
    contract = json.loads(contract_path.read_text())
    expected = contract["components"]["schemas"]["Health"]
    actual = application.openapi()["components"]["schemas"]["Health"]
    # Pydantic adds descriptive titles; compare every structural constraint in the contract.
    actual.pop("title")
    actual["properties"]["status"].pop("title")
    assert actual == expected
    operation = application.openapi()["paths"]["/api/v1/health"]["get"]
    expected_operation = contract["paths"]["/api/v1/health"]["get"]
    assert operation["operationId"] == expected_operation["operationId"]
    assert (
        operation["responses"]["200"]["content"]
        == expected_operation["responses"]["200"]["content"]
    )
    assert not operation.get("security")


@pytest.mark.parametrize("payload", [{"status": 1}, {"status": "error"}, {"status": "ok", "x": 1}])
def test_health_is_strict(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Health.model_validate(payload)


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MONETAE_DATABASE_URL", "postgresql+psycopg://example:change-me@db/example")
    monkeypatch.setenv("MONETAE_ENVIRONMENT", "test")
    monkeypatch.setenv("MONETAE_CORS_ORIGINS", '["http://localhost:3000"]')
    settings = Settings()
    assert settings.environment == "test"
    assert settings.database_url == "postgresql+psycopg://example:change-me@db/example"
    assert settings.cors_origins == ["http://localhost:3000"]


def test_settings_have_no_secret_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("MONETAE_DATABASE_URL", "MONETAE_ENVIRONMENT", "MONETAE_CORS_ORIGINS"):
        monkeypatch.delenv(key, raising=False)
    settings = Settings()
    assert settings.database_url is None
    assert settings.environment == "local"
    assert settings.cors_origins == []


def test_settings_are_strict() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"cors_origins": "http://localhost:3000"})
    with pytest.raises(ValidationError):
        Settings.model_validate({"environment": "unknown"})


@pytest.mark.parametrize("origin", ["http://localhost:3000", "https://untrusted.example"])
def test_cors_denied_by_default(client: TestClient, origin: str) -> None:
    response = client.get("/api/v1/health", headers={"Origin": origin})
    assert "access-control-allow-origin" not in response.headers
    preflight = client.options(
        "/api/v1/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers


def test_cors_allows_only_configured_origin() -> None:
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    with TestClient(app) as client:
        allowed = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
        denied = client.get("/api/v1/health", headers={"Origin": "https://untrusted.example"})
        assert "access-control-allow-origin" not in denied.headers
