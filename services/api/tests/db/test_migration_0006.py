from sqlalchemy import Engine, inspect

from alembic import command

from .conftest import migration_config


def test_migration_0006_roundtrip_and_no_drift(database_url: str, db_engine: Engine) -> None:
    config = migration_config(database_url)
    for _ in range(2):
        command.downgrade(config, "0005")
        inspector = inspect(db_engine)
        assert not {"subscriptions", "recurring_rules"} & set(inspector.get_table_names())
        assert "fk_transactions_recurring_rule_owner" not in {
            fk["name"] for fk in inspector.get_foreign_keys("transactions")
        }
        command.upgrade(config, "head")
        command.check(config)
    inspector = inspect(db_engine)
    for table in ("subscriptions", "recurring_rules"):
        assert {tuple(fk["constrained_columns"]) for fk in inspector.get_foreign_keys(table)} >= {
            ("account_id", "user_id"),
            ("account_id", "currency"),
            ("category_id", "user_id"),
        }
    assert ("recurring_rule_id", "user_id") in {
        tuple(fk["constrained_columns"]) for fk in inspector.get_foreign_keys("transactions")
    }
    assert ("subscription_id", "user_id") in {
        tuple(fk["constrained_columns"]) for fk in inspector.get_foreign_keys("recurring_rules")
    }


def test_roundtrip_with_materialized_payment_preserves_transactions(
    database_url: str, db_engine: Engine
) -> None:
    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy import delete, select
    from sqlalchemy.orm import Session

    from monetae.api.schemas.subscriptions import SubscriptionCreate
    from monetae.db.models import Account, Transaction, User
    from monetae.services.auth import SystemClock
    from monetae.services.subscriptions import SubscriptionService

    config = migration_config(database_url)
    command.downgrade(config, "0005")
    command.upgrade(config, "0006")
    with Session(db_engine) as db:
        user = User(email=f"migration-{uuid4().hex}@example.test", report_currency="PEN")
        db.add(user)
        db.flush()
        user_id = user.id
        account = Account(user_id=user.id, name="Synthetic", type="cash", currency="PEN")
        db.add(account)
        db.flush()
        SubscriptionService(db, "synthetic-cursor-secret", SystemClock()).create(
            user.id,
            SubscriptionCreate.model_validate(
                {
                    "title": "Netflix",
                    "amount": "30.00",
                    "currency": "PEN",
                    "account_id": account.id,
                    "period": "monthly",
                    "next_due_on": "2026-11-01",
                }
            ),
        )
        before = list(db.scalars(select(Transaction).where(Transaction.user_id == user_id)))
        assert len(before) == 1 and before[0].amount == Decimal("-30.00")
        transaction_id = before[0].id
        # Captura todas las columnas para demostrar que solo cambia la referencia.
        snapshot = {
            column.name: getattr(before[0], column.name) for column in Transaction.__table__.columns
        }
        db.commit()
    try:
        command.downgrade(config, "0005")
        with Session(db_engine) as db:
            after = list(db.scalars(select(Transaction).where(Transaction.user_id == user_id)))
            assert len(after) == 1 and after[0].id == transaction_id
            for column in Transaction.__table__.columns:
                expected = None if column.name == "recurring_rule_id" else snapshot[column.name]
                assert getattr(after[0], column.name) == expected
        command.upgrade(config, "0006")
        command.check(config)
        with Session(db_engine) as db:
            row = db.get(Transaction, transaction_id)
            assert row is not None and row.amount == Decimal("-30.00")
            assert row.status == "scheduled" and row.recurring_rule_id is None
    finally:
        command.upgrade(config, "head")
        with Session(db_engine) as db:
            for model in (Transaction, Account):
                db.execute(delete(model).where(model.user_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
            db.commit()
