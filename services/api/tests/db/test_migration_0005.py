from sqlalchemy import Engine, inspect

from alembic import command

from .conftest import migration_config


def test_migration_0005_roundtrip_and_no_drift(database_url: str, db_engine: Engine) -> None:
    config = migration_config(database_url)
    for _ in range(2):
        command.downgrade(config, "0004")
        inspector = inspect(db_engine)
        assert not {"loans", "loan_movements"} & set(inspector.get_table_names())
        assert "uq_people_id_user_id" not in {
            c["name"] for c in inspector.get_unique_constraints("people")
        }
        command.upgrade(config, "head")
        command.check(config)
    inspector = inspect(db_engine)
    columns = {c["name"] for c in inspector.get_columns("loans")}
    assert "outstanding" not in columns and "status" not in columns
    assert "sequence" in {c["name"] for c in inspector.get_columns("loan_movements")}
    assert {
        tuple(fk["constrained_columns"]) for fk in inspector.get_foreign_keys("loan_movements")
    } >= {("loan_id", "user_id"), ("transaction_id", "user_id")}
