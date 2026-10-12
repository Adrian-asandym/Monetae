"""Backfill, idempotent seeds, constraints and non-destructive downgrade."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from monetae.db.models import Account, Transaction, User

from .conftest import migration_config


def test_migration_0012_existing_user_and_downgrade(database_url: str, db_engine: Engine) -> None:
    config = migration_config(database_url)
    command.downgrade(config, "0011")
    user_id, account_id, group_id = uuid4(), uuid4(), uuid4()
    try:
        with db_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, email, report_currency) "
                    "VALUES (:id, 'migration-0012@example.test', 'PEN')"
                ),
                {"id": user_id},
            )
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        command.check(config)
        with db_engine.begin() as connection:
            categories = connection.execute(
                text("SELECT id, kind, system_key FROM categories WHERE user_id = :user_id"),
                {"user_id": user_id},
            ).all()
            assert {c.system_key for c in categories} == {
                "balance_correction_income",
                "balance_correction_expense",
            }
            connection.execute(
                text(
                    "INSERT INTO accounts (id, user_id, name, type, currency) "
                    "VALUES (:id, :user_id, 'Synthetic', 'cash', 'PEN')"
                ),
                {"id": account_id, "user_id": user_id},
            )
            for category in categories:
                connection.execute(
                    text("""
                    INSERT INTO transactions (user_id, account_id, category_id, kind, amount,
                        currency, occurred_at, status, title, fx_rate_to_base, fx_rate_source,
                        source, transfer_group_id)
                    VALUES (:user_id, :account_id, :category_id, :kind, :amount, 'PEN', now(),
                        'posted', 'Synthetic correction', 1, 'manual', 'web', :group_id)
                """),
                    {
                        "user_id": user_id,
                        "account_id": account_id,
                        "category_id": category.id,
                        "kind": category.kind,
                        "amount": 10 if category.kind == "income" else -10,
                        "group_id": group_id,
                    },
                )
        command.downgrade(config, "0011")
        with db_engine.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM transactions WHERE user_id=:id"), {"id": user_id}
                )
                == 2
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM transactions WHERE user_id=:id "
                        "AND transfer_group_id IS NOT NULL"
                    ),
                    {"id": user_id},
                )
                == 0
            )
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM categories WHERE user_id=:id AND is_system"),
                    {"id": user_id},
                )
                == 0
            )
        command.upgrade(config, "head")
        command.check(config)
        with db_engine.connect() as connection:
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM categories WHERE user_id=:id "
                        "AND system_key LIKE 'balance_correction_%'"
                    ),
                    {"id": user_id},
                )
                == 2
            )
        indexes = {i["name"]: i for i in inspect(db_engine).get_indexes("transactions")}
        assert indexes["uq_transactions_correction_outgoing"]["unique"]
        assert indexes["uq_transactions_correction_incoming"]["unique"]
    finally:
        command.upgrade(config, "head")
        with db_engine.begin() as connection:
            for table in ("transactions", "categories", "accounts"):
                # Table names are an internal fixed list, all values remain bound.
                connection.execute(text(f"DELETE FROM {table} WHERE user_id=:id"), {"id": user_id})
            connection.execute(text("DELETE FROM users WHERE id=:id"), {"id": user_id})


def test_correction_group_unique_direction_and_transfer_requires_group(
    db_session: Session, users: tuple[User, User]
) -> None:
    account = Account(user_id=users[0].id, name="Synthetic", type="cash", currency="PEN")
    db_session.add(account)
    db_session.flush()
    group = uuid4()

    def leg(kind: str, amount: int, group_id: UUID | None) -> Transaction:
        return Transaction(
            user_id=users[0].id,
            account_id=account.id,
            kind=kind,
            amount=Decimal(amount),
            currency="PEN",
            occurred_at=datetime.now(UTC),
            status="posted",
            title="Synthetic",
            fx_rate_to_base=Decimal("1.000000"),
            fx_rate_source="manual",
            source="web",
            transfer_group_id=group_id,
        )

    db_session.add_all([leg("expense", -10, group), leg("income", 10, group)])
    db_session.flush()
    for kind, amount, group_id in (
        ("expense", -5, group),
        ("income", 5, group),
        ("transfer", 5, None),
        ("loan", 5, group),
    ):
        with pytest.raises(IntegrityError), db_session.begin_nested():
            db_session.add(leg(kind, amount, group_id))
            db_session.flush()
