"""Cada ejecución utiliza una base temporal, nunca la BD de la aplicación."""

import os
from argparse import Namespace
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from alembic import command
from monetae.db.models import User

API_ROOT = Path(__file__).resolve().parents[2]


def migration_config(url: str) -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.cmd_opts = Namespace(x=[f"url={url}"])
    return config


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    server_url = make_url(
        os.environ.get(
            "MONETAE_TEST_DATABASE_URL",
            "postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres",
        )
    )
    admin = create_engine(
        server_url,
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 3, "options": "-c timezone=UTC"},
    )
    name = f"monetae_test_{uuid4().hex}"
    quoted_name = admin.dialect.identifier_preparer.quote(name)
    try:
        try:
            with admin.connect() as connection:
                connection.execute(text("SELECT 1"))
        except OperationalError:
            message = "PostgreSQL de pruebas no accesible; configura MONETAE_TEST_DATABASE_URL"
            if os.environ.get("MONETAE_REQUIRE_DB") == "1":
                pytest.fail(message)
            pytest.skip(message)
        with admin.connect() as connection:
            connection.exec_driver_sql(f"CREATE DATABASE {quoted_name}")
        url = server_url.set(database=name).render_as_string(hide_password=False)
        try:
            command.upgrade(migration_config(url), "head")
            yield url
        finally:
            with admin.connect() as connection:
                connection.exec_driver_sql(f"DROP DATABASE {quoted_name} WITH (FORCE)")
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def db_engine(database_url: str) -> Iterator[Engine]:
    engine = create_engine(database_url, connect_args={"options": "-c timezone=UTC"})
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    with db_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def users(db_session: Session) -> tuple[User, User]:
    first = User(email="first@example.test", report_currency="PEN")
    second = User(email="second@example.test", report_currency="USD")
    db_session.add_all([first, second])
    db_session.flush()
    return first, second
