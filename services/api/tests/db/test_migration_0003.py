from sqlalchemy import Engine, inspect, text

from alembic import command

from .conftest import migration_config


def test_migration_0003_roundtrip_and_no_drift(database_url: str, db_engine: Engine) -> None:
    config = migration_config(database_url)
    command.downgrade(config, "0002")
    inspector = inspect(db_engine)
    assert "transactions" not in inspector.get_table_names()
    for table in ("accounts", "categories", "tags"):
        assert ["id", "user_id"] not in [
            u["column_names"] for u in inspector.get_unique_constraints(table)
        ]
    command.upgrade(config, "0003")
    assert_ledger_schema(db_engine)
    command.upgrade(config, "head")
    command.check(config)
    command.downgrade(config, "0002")
    command.upgrade(config, "0003")
    assert_ledger_schema(db_engine)
    command.upgrade(config, "head")
    command.check(config)


def assert_ledger_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    expected = {
        "transactions": {
            (("account_id", "user_id"), "accounts", ("id", "user_id")),
            (("account_id", "currency"), "accounts", ("id", "currency")),
            (("category_id", "user_id"), "categories", ("id", "user_id")),
        },
        "transaction_tags": {
            (("transaction_id", "user_id"), "transactions", ("id", "user_id")),
            (("tag_id", "user_id"), "tags", ("id", "user_id")),
        },
    }
    for table, foreign_keys in expected.items():
        actual = {
            (tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]))
            for f in inspector.get_foreign_keys(table)
        }
        assert foreign_keys <= actual
    for table in ("accounts", "categories", "tags", "transactions"):
        assert ["id", "user_id"] in [
            u["column_names"] for u in inspector.get_unique_constraints(table)
        ]
    with engine.connect() as connection:
        definitions: dict[str, str] = dict(
            connection.execute(
                text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename='transactions'")
            ).all()
        )
    indexes = {
        k: v for k, v in definitions.items() if k.startswith(("ix_", "uq_transactions_user_"))
    }
    assert len(indexes) == 6
    assert all("deleted_at IS NULL" in v for v in indexes.values())
    assert "USING gin" in indexes["ix_transactions_search"]
    assert "occurred_at DESC" in indexes["ix_transactions_user_occurred"]
    assert "import_external_id IS NOT NULL" in indexes["uq_transactions_user_import_external"]
    assert not any(
        f["constrained_columns"] == ["recurring_rule_id"]
        for f in inspector.get_foreign_keys("transactions")
    )
