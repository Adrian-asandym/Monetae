from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from monetae.api.errors import register_exception_handlers
from monetae.api.routers.health import router as health_router
from monetae.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    application = FastAPI(title="Monetae API", version="0.1.0")
    application.state.settings = config
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
    )
    register_exception_handlers(application)
    application.include_router(health_router)
    return application


app = create_app()
