"""Cookies firmadas, validación de origen y dependencias de autenticación."""

import hashlib
import hmac
import secrets
from collections.abc import Generator
from dataclasses import dataclass
from http import HTTPStatus
from typing import Annotated, cast
from urllib.parse import urlsplit

from fastapi import Depends, Request, Response
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session as DbSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse

from monetae.api.errors import Problem, problem_response, unhandled_exception_handler
from monetae.api.schemas.auth import CurrentUser
from monetae.config import Settings
from monetae.db.models import Session, User
from monetae.db.session import create_session_factory
from monetae.services.auth import AuthError, AuthService, Clock, token_hash

SESSION_COOKIE = "monetae_session"
CSRF_COOKIE = "monetae_csrf"
SESSION_SECURITY = APIKeyCookie(name=SESSION_COOKIE, scheme_name="SessionCookie", auto_error=False)


def settings_for(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def clock_for(request: Request) -> Clock:
    return cast(Clock, request.app.state.clock)


def database(request: Request) -> Generator[DbSession, None, None]:
    with create_session_factory(settings_for(request))() as db:
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise


# scope="function": el commit corre al terminar el endpoint, ANTES de enviar la
# respuesta. Con el alcance por defecto (request) FastAPI >= 0.118 lo ejecuta
# después, y el cliente puede leer antes de que la escritura sea visible.
Database = Annotated[DbSession, Depends(database, scope="function")]


def auth_service(request: Request, db: Database) -> AuthService:
    return AuthService(db, settings_for(request), clock_for(request))


Service = Annotated[AuthService, Depends(auth_service)]


@dataclass(frozen=True)
class Identity:
    user: User
    session: Session


def current_identity(
    service: Service, token: Annotated[str | None, Depends(SESSION_SECURITY)]
) -> Identity:
    return Identity(*service.authenticate(token))


Authenticated = Annotated[Identity, Depends(current_identity)]


def profile(user: User) -> CurrentUser:
    return CurrentUser.model_validate(
        {
            "id": user.id,
            "email": user.email,
            "preferences": user.preferences,
            "pin_configured": user.pin_hash is not None,
            "locked": False,
            "webauthn_enabled": False,
            "timezone": user.timezone,
            "base_currency": user.base_currency,
            "locale": user.locale,
            "lock_after_minutes": user.lock_after_minutes,
            "report_currency": user.report_currency,
        }
    )


def _binding(token: str | None) -> str:
    return token_hash(token).hex() if token else "pre"


def csrf_signature(nonce: str, token: str | None, settings: Settings) -> str:
    return hmac.new(
        settings.secret_key.encode(), (nonce + _binding(token)).encode(), hashlib.sha256
    ).hexdigest()


def new_csrf(token: str | None, settings: Settings) -> str:
    nonce = secrets.token_urlsafe(32)
    return nonce + "." + csrf_signature(nonce, token, settings)


def valid_csrf(value: str | None, token: str | None, settings: Settings) -> bool:
    if not value or len(value) > 160:
        return False
    nonce, separator, signature = value.partition(".")
    if not separator or len(nonce) != 43 or not nonce.isascii() or not signature.isascii():
        return False
    return hmac.compare_digest(signature, csrf_signature(nonce, token, settings))


def csrf_cookie(response: Response, value: str, settings: Settings) -> None:
    response.set_cookie(
        CSRF_COOKIE, value, secure=settings.cookie_secure, httponly=False, samesite="lax", path="/"
    )


def session_cookie(response: Response, value: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        value,
        max_age=settings.session_absolute_days * 86400,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )


def clear_session(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        SESSION_COOKIE, secure=settings.cookie_secure, httponly=True, samesite="lax", path="/"
    )
    csrf_cookie(response, new_csrf(None, settings), settings)


def origin(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            return None
        port = parsed.port
        suffix = f":{port}" if port and port != (443 if parsed.scheme == "https" else 80) else ""
        host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
        return f"{parsed.scheme}://{host}{suffix}"
    except ValueError:
        return None


def trusted_origin(request: Request, settings: Settings) -> bool:
    value = request.headers.get("origin")
    if value is not None:
        try:
            parsed = urlsplit(value)
        except ValueError:
            return False
        if parsed.path or parsed.query or parsed.fragment:
            return False
    else:
        value = request.headers.get("referer", "")
    candidate = origin(value)
    allowed = {origin(str(request.base_url)), *(origin(item) for item in settings.cors_origins)}
    return candidate is not None and candidate in allowed


class CsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        settings = settings_for(request)
        cookie = request.cookies.get(CSRF_COOKIE)
        token = request.cookies.get(SESSION_COOKIE)
        valid = valid_csrf(cookie, token, settings)
        header = request.headers.get("x-csrf-token", "")
        response: StarletteResponse
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not (
            valid
            and cookie is not None
            and header.isascii()
            and cookie.isascii()
            and hmac.compare_digest(header, cookie)
            and trusted_origin(request, settings)
        ):
            response = problem_response(
                Problem(
                    type="about:blank",
                    title="Forbidden",
                    status=403,
                    detail="CSRF validation failed.",
                    code="csrf_failed",
                    instance=request.url.path,
                )
            )
        else:
            try:
                response = await call_next(request)
            except Exception as exc:
                response = await _safe_error(request, exc)
        # Routers deliberately rotate the cookie after login/logout. Do not overwrite it.
        if not valid and not any(
            h.startswith(CSRF_COOKIE + "=") for h in response.headers.getlist("set-cookie")
        ):
            csrf_cookie(response, new_csrf(token, settings), settings)
        if request.url.path.startswith(("/api/v1/auth", "/api/v1/users")):
            response.headers["Cache-Control"] = "no-store"
        return response


async def auth_exception_handler(request: Request, exc: Exception) -> StarletteResponse:
    assert isinstance(exc, AuthError)
    return problem_response(
        Problem(
            type="about:blank",
            title=HTTPStatus(exc.status).phrase,
            status=exc.status,
            detail=exc.detail,
            code=exc.code,
            instance=request.url.path,
        ),
        headers={"Retry-After": str(exc.retry)} if exc.retry else None,
    )


async def _safe_error(request: Request, exc: Exception) -> StarletteResponse:
    # Keep the existing sanitized 500 response inside the cookie-issuing middleware.
    return unhandled_exception_handler(request, exc)
