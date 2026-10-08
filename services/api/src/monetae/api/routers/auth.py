from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response

from monetae.api.errors import Problem
from monetae.api.schemas.auth import (
    ActionResult,
    AuthenticatedSession,
    GoogleLogin,
    LoginRequest,
    LoginResult,
    Session,
    SessionPage,
)
from monetae.api.security import (
    Authenticated,
    Service,
    clear_session,
    csrf_cookie,
    new_csrf,
    profile,
    session_cookie,
    settings_for,
    valid_csrf,
)
from monetae.services.auth import AuthError

# Pydantic returns untyped schema dictionaries at this OpenAPI boundary.
# Inline FieldError so an embedded schema never refers to a nonexistent root $defs.
PROBLEM_SCHEMA = Problem.model_json_schema()
PROBLEM_SCHEMA["properties"]["errors"]["anyOf"][0]["items"] = PROBLEM_SCHEMA.pop("$defs")[
    "FieldError"
]

ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    status: {
        "content": {"application/problem+json": {"schema": PROBLEM_SCHEMA}},
        "description": "Error RFC 9457.",
    }
    for status in (400, 401, 403, 404, 409, 422)
}
router = APIRouter(prefix="/api/v1/auth", tags=["auth"], responses=ERROR_RESPONSES)
CsrfHeader = Annotated[str, Header(alias="X-CSRF-Token")]


@router.post(
    "/login",
    response_model=LoginResult,
    response_model_exclude_unset=True,
    responses={
        429: {
            "description": "Too many attempts",
            "content": {"application/problem+json": {"schema": PROBLEM_SCHEMA}},
        },
        501: {
            "description": "Google login deferred",
            "content": {"application/problem+json": {"schema": PROBLEM_SCHEMA}},
        },
    },
    operation_id="login",
    openapi_extra={"security": []},
)
def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    service: Service,
    csrf: CsrfHeader,
) -> AuthenticatedSession:
    if isinstance(payload, GoogleLogin):
        raise AuthError(501, "google_login_not_available", "Google login is not available yet.")
    user, session, token = service.login(
        payload.email,
        payload.password.get_secret_value(),
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", ""),
    )
    config = settings_for(request)
    csrf_value = new_csrf(token, config)
    session_cookie(response, token, config)
    csrf_cookie(response, csrf_value, config)
    return AuthenticatedSession(
        user=profile(user), csrf_token=csrf_value, expires_at=session.expires_at
    )


@router.post("/logout", response_model=ActionResult, operation_id="logout")
def logout(
    request: Request,
    response: Response,
    identity: Authenticated,
    service: Service,
    csrf: CsrfHeader,
) -> ActionResult:
    count = service.revoke(identity.user.id, identity.session.id)
    clear_session(response, settings_for(request))
    return ActionResult(success=True, affected_count=count)


@router.post("/logout-all", response_model=ActionResult, operation_id="logout_all")
def logout_all(
    request: Request,
    response: Response,
    identity: Authenticated,
    service: Service,
    csrf: CsrfHeader,
) -> ActionResult:
    count = service.revoke(identity.user.id)
    clear_session(response, settings_for(request))
    return ActionResult(success=True, affected_count=count)


@router.get("/sessions", response_model=SessionPage, operation_id="list_sessions")
def list_sessions(
    identity: Authenticated,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
) -> SessionPage:
    rows, next_cursor = service.list_sessions(identity.user.id, limit, cursor)
    return SessionPage(
        items=[
            Session(
                id=row.id,
                created_at=row.created_at,
                last_seen_at=row.last_seen_at,
                expires_at=service.expiration(row),
                user_agent=row.user_agent or "",
                ip=row.ip or "",
                is_current=row.id == identity.session.id,
            )
            for row in rows
        ],
        next_cursor=next_cursor,
    )


@router.delete("/sessions/{id}", response_model=ActionResult, operation_id="revoke_session")
def revoke_session(
    id: UUID,
    request: Request,
    response: Response,
    identity: Authenticated,
    service: Service,
    csrf: CsrfHeader,
) -> ActionResult:
    count = service.revoke(identity.user.id, id)
    if id == identity.session.id:
        clear_session(response, settings_for(request))
    return ActionResult(success=True, affected_count=count)


@router.get(
    "/csrf",
    response_model=AuthenticatedSession,
    response_model_exclude_unset=True,
    operation_id="get_csrf_token",
)
def get_csrf_token(
    request: Request, response: Response, identity: Authenticated, service: Service
) -> AuthenticatedSession:
    config = settings_for(request)
    token = request.cookies.get("monetae_session")
    value = request.cookies.get("monetae_csrf")
    if not valid_csrf(value, token, config) or value is None:
        value = new_csrf(token, config)
        csrf_cookie(response, value, config)
    return AuthenticatedSession(
        user=profile(identity.user),
        csrf_token=value,
        expires_at=service.expiration(identity.session),
    )
