"""Sesiones síncronas con commit al completar y rollback ante errores."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from monetae.config import Settings


@lru_cache(maxsize=8)
def _engine_for_url(database_url: str) -> Engine:
    return create_engine(
        database_url, pool_pre_ping=True, connect_args={"options": "-c timezone=UTC"}
    )


def get_engine(settings: Settings) -> Engine:
    if settings.database_url is None:
        raise ValueError("MONETAE_DATABASE_URL is required for database access")
    return _engine_for_url(settings.database_url)


def create_session_factory(settings: Settings) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(settings), expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    factory = create_session_factory(Settings())
    with factory() as session:
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
