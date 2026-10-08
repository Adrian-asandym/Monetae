"""Alembic usa Settings; -x url= permite seleccionar una BD explícita."""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

import monetae.db.models  # noqa: F401 -- registra tablas para autogenerate
from alembic import context
from monetae.config import Settings
from monetae.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def migration_url() -> str:
    url = context.get_x_argument(as_dictionary=True).get("url") or Settings().database_url
    if not url:
        raise ValueError("Set MONETAE_DATABASE_URL or pass alembic -x url=...")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=migration_url(),
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(
        migration_url(), poolclass=pool.NullPool, connect_args={"options": "-c timezone=UTC"}
    )
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection, target_metadata=Base.metadata, compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
