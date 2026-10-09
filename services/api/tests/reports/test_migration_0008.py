"""The authorized global-rate migration is reversible and matches metadata."""

from conftest import migration_config
from sqlalchemy import Engine, inspect

from alembic import command


def test_exchange_rates_roundtrip(database_url: str, db_engine: Engine) -> None:
    config = migration_config(database_url)
    command.downgrade(config, "0007")
    assert "exchange_rates" not in inspect(db_engine).get_table_names()
    command.upgrade(config, "0008")
    columns = {column["name"] for column in inspect(db_engine).get_columns("exchange_rates")}
    assert columns == {
        "id",
        "from_currency",
        "to_currency",
        "rate",
        "as_of",
        "source",
        "created_at",
        "updated_at",
    }
    command.check(config)
    command.downgrade(config, "0007")
    assert "exchange_rates" not in inspect(db_engine).get_table_names()
    command.upgrade(config, "head")
