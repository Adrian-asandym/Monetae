import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, ValidationError

from monetae.api.errors import Problem


class TestPayload(BaseModel):
    __test__ = False
    model_config = ConfigDict(strict=True, extra="forbid")
    count: int


def assert_problem(response_status: int, content: bytes, content_type: str) -> Problem:
    assert content_type == "application/problem+json"
    problem = Problem.model_validate_json(content)
    assert problem.status == response_status
    assert problem.type == "about:blank"
    assert problem.title
    assert problem.detail
    return problem


@pytest.mark.parametrize(
    "method,path,status", [("GET", "/api/v1/missing", 404), ("POST", "/api/v1/health", 405)]
)
def test_http_errors(client: TestClient, method: str, path: str, status: int) -> None:
    response = client.request(method, path)
    assert response.status_code == status
    problem = assert_problem(status, response.content, response.headers["content-type"])
    assert problem.instance == path
    if status == 405:
        assert response.headers["allow"] == "GET"


def test_http_exception_headers(application: FastAPI, client: TestClient) -> None:
    @application.get("/limited", response_model=None)
    def limited() -> None:
        raise HTTPException(429, detail="Try again later.", headers={"Retry-After": "10"})

    response = client.get("/limited")
    problem = assert_problem(429, response.content, response.headers["content-type"])
    assert problem.detail == "Try again later."
    assert response.headers["retry-after"] == "10"


@pytest.mark.parametrize(
    "payload", [{"count": "private-input"}, {"count": 1, "extra": "private-input"}, {}]
)
def test_validation_errors(
    application: FastAPI, client: TestClient, payload: dict[str, object]
) -> None:
    @application.post("/validate", response_model=TestPayload)
    def validate(body: TestPayload) -> TestPayload:
        return body

    response = client.post("/validate", json=payload)
    assert response.status_code == 422
    problem = assert_problem(422, response.content, response.headers["content-type"])
    assert problem.errors
    assert problem.errors[0].field.startswith("body.")
    assert problem.errors[0].code
    assert "private-input" not in response.text
    assert "input" not in response.json()["errors"][0]


def test_malformed_json(application: FastAPI, client: TestClient) -> None:
    @application.post("/validate", response_model=TestPayload)
    def validate(body: TestPayload) -> TestPayload:
        return body

    response = client.post("/validate", content="{", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    problem = assert_problem(422, response.content, response.headers["content-type"])
    assert problem.errors
    assert problem.errors[0].code == "json_invalid"


def test_internal_error_does_not_leak(application: FastAPI, client: TestClient) -> None:
    @application.get("/broken", response_model=None)
    def broken() -> None:
        raise RuntimeError("private-secret-database-details")

    response = client.get("/broken")
    assert response.status_code == 500
    problem = assert_problem(500, response.content, response.headers["content-type"])
    assert problem.detail == "An unexpected error occurred."
    assert "private-secret" not in response.text
    assert "RuntimeError" not in response.text


@pytest.mark.parametrize("status", ["404", True, 399, 600])
def test_problem_is_strict(status: object) -> None:
    with pytest.raises(ValidationError):
        Problem.model_validate(
            {"type": "about:blank", "title": "Error", "status": status, "detail": "Error"}
        )
