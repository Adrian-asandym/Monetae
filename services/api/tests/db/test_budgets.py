"""Database ownership defense, checks and reversible migration."""

from datetime import date
from decimal import Decimal

import pytest
from conftest import migration_config
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from monetae.db.models import (
    Account,
    Budget,
    BudgetCategory,
    BudgetTransaction,
    Category,
    Transaction,
    User,
)


def budget(user: User) -> Budget:
    return Budget(
        user_id=user.id,
        name="Synthetic",
        period="monthly",
        start_on=date(2026, 10, 1),
        amount=Decimal("100.00"),
        currency="PEN",
        scope="all",
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("period", "yearly"),
        ("scope", "other"),
        ("amount", Decimal(0)),
        ("amount", Decimal(-1)),
        ("period", "custom"),
        ("end_on", date(2026, 9, 30)),
        ("currency", "pen"),
    ],
)
def test_budget_checks(
    db_session: Session, users: tuple[User, User], field: str, value: object
) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        row = budget(users[0])
        setattr(row, field, value)
        db_session.add(row)
        db_session.flush()


@pytest.mark.parametrize("link_kind", ["category", "transaction"])
@pytest.mark.parametrize("foreign", ["budget", "reference"])
def test_link_composite_ownership(
    db_session: Session, users: tuple[User, User], link_kind: str, foreign: str
) -> None:
    owner, other = users
    row = budget(other if foreign == "budget" else owner)
    reference_owner = other if foreign == "reference" else owner
    category = Category(user_id=reference_owner.id, name="Synthetic", kind="expense")
    account = Account(user_id=reference_owner.id, name="Synthetic", type="cash", currency="PEN")
    db_session.add_all([row, category, account])
    db_session.flush()
    transaction = Transaction(
        user_id=reference_owner.id,
        account_id=account.id,
        currency="PEN",
        kind="expense",
        amount=Decimal(-1),
        occurred_at=account.created_at,
        status="posted",
        title="Synthetic",
        fx_rate_to_base=Decimal(1),
        fx_rate_source="manual",
        source="web",
    )
    db_session.add(transaction)
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        if link_kind == "category":
            db_session.add(
                BudgetCategory(
                    user_id=owner.id,
                    budget_id=row.id,
                    category_id=category.id,
                    limit_amount=Decimal(0),
                )
            )
        else:
            db_session.add(
                BudgetTransaction(user_id=owner.id, budget_id=row.id, transaction_id=transaction.id)
            )
        db_session.flush()


def test_category_limit_nonnegative(db_session: Session, users: tuple[User, User]) -> None:
    row = budget(users[0])
    category = Category(user_id=users[0].id, name="Synthetic", kind="expense")
    db_session.add_all([row, category])
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            BudgetCategory(
                user_id=users[0].id,
                budget_id=row.id,
                category_id=category.id,
                limit_amount=Decimal(-1),
            )
        )
        db_session.flush()


def test_budget_migration_roundtrip(database_url: str, db_engine: Engine) -> None:
    config = migration_config(database_url)
    tables = {"budgets", "budget_categories", "budget_transactions"}
    for _ in range(2):
        command.downgrade(config, "0008")
        assert not tables.intersection(inspect(db_engine).get_table_names())
        command.upgrade(config, "head")
        assert tables <= set(inspect(db_engine).get_table_names())
        command.check(config)
