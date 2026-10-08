from collections.abc import Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse


class FieldError(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    field: str
    message: str
    code: str


class Problem(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    type: str
    title: str
    status: int = Field(ge=400, le=599)
    detail: str
    instance: str | None = None
    code: str | None = None
    errors: list[FieldError] | None = None


def problem_response(problem: Problem, headers: Mapping[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(mode="json", exclude_none=True),
        media_type="application/problem+json",
        headers=headers,
    )


def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    try:
        title = HTTPStatus(exc.status_code).phrase
    except ValueError:
        title = "HTTP Error"
    return problem_response(
        Problem(
            type="about:blank",
            title=title,
            status=exc.status_code,
            detail=str(exc.detail),
            instance=request.url.path,
        ),
        headers=exc.headers,
    )


def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # FastAPI exposes untyped error dictionaries at this boundary. Copy only the contract fields;
    # never serialize input values or context, which can contain secrets or non-JSON objects.
    errors = [
        FieldError(
            field=".".join(str(part) for part in error["loc"]),
            message=str(error["msg"]),
            code=str(error["type"]),
        )
        for error in exc.errors()
    ]
    return problem_response(
        Problem(
            type="about:blank",
            title="Unprocessable Entity",
            status=422,
            detail="Request validation failed.",
            instance=request.url.path,
            errors=errors,
        )
    )


def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return problem_response(
        Problem(
            type="about:blank",
            title="Internal Server Error",
            status=500,
            detail="An unexpected error occurred.",
            instance=request.url.path,
        )
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
