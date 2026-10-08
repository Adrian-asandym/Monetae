from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from monetae.api.errors import register_exception_handlers
from monetae.api.routers.accounts import router as accounts_router
from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.routers.auth import router as auth_router
from monetae.api.routers.categories import router as categories_router
from monetae.api.routers.health import router as health_router
from monetae.api.routers.people import router as people_router
from monetae.api.routers.tags import router as tags_router
from monetae.api.routers.users import router as users_router
from monetae.api.security import CsrfMiddleware, auth_exception_handler
from monetae.config import Settings
from monetae.services.auth import AuthError, SystemClock


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    application = FastAPI(title="Monetae API", version="0.1.0")
    application.state.settings = config
    application.state.clock = SystemClock()
    application.add_exception_handler(AuthError, auth_exception_handler)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
    )
    application.add_middleware(CsrfMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router, responses=ERROR_RESPONSES)
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(accounts_router)
    application.include_router(categories_router)
    application.include_router(people_router)
    application.include_router(tags_router)
    return application


app = create_app()
