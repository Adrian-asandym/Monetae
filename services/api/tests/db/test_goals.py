"""Database ownership defense, checks and reversible migration."""

from decimal import Decimal

import pytest
from conftest import migration_config
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from monetae.db.models import (
    Account,
    Goal,
    GoalTransaction,
    Transaction,
    User,
)


def goal(user: User) -> Goal:
    return Goal(
        user_id=user.id,
        name="Synthetic",
        kind="save",
        target_amount=Decimal("100.00"),
        currency="PEN",
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "loan"),
        ("target_amount", Decimal(0)),
        ("target_amount", Decimal(-1)),
        ("currency", "pen"),
        ("color", "red"),
        ("icon", ""),
        ("icon", "x" * 65),
    ],
)
def test_goal_checks(
    db_session: Session, users: tuple[User, User], field: str, value: object
) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        row = goal(users[0])
        setattr(row, field, value)
        db_session.add(row)
        db_session.flush()


@pytest.mark.parametrize("foreign", ["goal", "reference"])
def test_link_composite_ownership(
    db_session: Session, users: tuple[User, User], foreign: str
) -> None:
    owner, other = users
    row = goal(other if foreign == "goal" else owner)
    reference_owner = other if foreign == "reference" else owner
    account = Account(user_id=reference_owner.id, name="Synthetic", type="cash", currency="PEN")
    db_session.add_all([row, account])
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
        db_session.add(
            GoalTransaction(user_id=owner.id, goal_id=row.id, transaction_id=transaction.id)
        )
        db_session.flush()


def test_goal_migration_roundtrip(database_url: str, db_engine: Engine) -> None:
    config = migration_config(database_url)
    tables = {"goals", "goal_transactions"}
    for _ in range(2):
        command.downgrade(config, "0009")
        assert not tables.intersection(inspect(db_engine).get_table_names())
        command.upgrade(config, "head")
        assert tables <= set(inspect(db_engine).get_table_names())
        command.check(config)
