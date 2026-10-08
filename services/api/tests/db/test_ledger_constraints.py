from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from monetae.db.models import Account, Category, Tag, Transaction, User


def seed(db: Session, users: tuple[User, User]) -> tuple[Account, Account, Category, Tag, Tag]:
    first, second = users
    a = Account(user_id=first.id, name="Local", type="cash", currency="PEN")
    b = Account(user_id=second.id, name="Foreign", type="cash", currency="PEN")
    category = Category(user_id=second.id, name="Foreign", kind="expense")
    t = Tag(user_id=first.id, name="Local")
    other = Tag(user_id=second.id, name="Foreign")
    db.add_all([a, b, category, t, other])
    db.flush()
    return a, b, category, t, other


@pytest.mark.parametrize("violation", ["account_owner", "category_owner", "account_currency"])
def test_direct_sql_transaction_foreign_keys(
    db_session: Session, users: tuple[User, User], violation: str
) -> None:
    local, foreign, category, _, _ = seed(db_session, users)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text("""
            INSERT INTO transactions (user_id, account_id, category_id, currency, kind, amount,
                occurred_at, status, title, fx_rate_to_base, fx_rate_source, source)
            VALUES (:user_id, :account_id, :category_id, :currency, 'expense', -1.00,
                now(), 'posted', 'Synthetic', 1.000000, 'manual', 'web')
        """),
            {
                "user_id": users[0].id,
                "account_id": foreign.id if violation == "account_owner" else local.id,
                "category_id": category.id if violation == "category_owner" else None,
                "currency": "USD" if violation == "account_currency" else "PEN",
            },
        )


@pytest.mark.parametrize("violation", ["transaction_owner", "tag_owner"])
def test_direct_sql_tag_links_foreign_keys(
    db_session: Session, users: tuple[User, User], violation: str
) -> None:
    local, foreign, _, tag, foreign_tag = seed(db_session, users)
    owner = users[1] if violation == "transaction_owner" else users[0]
    row = Transaction(
        user_id=owner.id,
        account_id=foreign.id if owner == users[1] else local.id,
        currency="PEN",
        kind="expense",
        amount=Decimal(-1),
        occurred_at=datetime.now(UTC),
        status="posted",
        title="Synthetic",
        fx_rate_to_base=Decimal(1),
        fx_rate_source="manual",
        source="web",
    )
    db_session.add(row)
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text(
                "INSERT INTO transaction_tags (user_id, transaction_id, tag_id) "
                "VALUES (:user_id, :transaction_id, :tag_id)"
            ),
            {
                "user_id": users[0].id,
                "transaction_id": row.id,
                "tag_id": foreign_tag.id if violation == "tag_owner" else tag.id,
            },
        )


@pytest.mark.parametrize(
    "column,value",
    [
        ("amount", "0"),
        ("fx_rate_to_base", "0"),
        ("kind", "invalid"),
        ("status", "invalid"),
        ("fx_rate_source", "invalid"),
        ("source", "invalid"),
        ("categorization_source", "invalid"),
        ("currency", "pen"),
    ],
)
def test_ledger_check_constraints(
    db_session: Session, users: tuple[User, User], column: str, value: str
) -> None:
    local, _, _, _, _ = seed(db_session, users)
    row = Transaction(
        user_id=users[0].id,
        account_id=local.id,
        currency="PEN",
        kind="expense",
        amount=Decimal(-1),
        occurred_at=datetime.now(UTC),
        status="posted",
        title="Synthetic",
        fx_rate_to_base=Decimal(1),
        fx_rate_source="manual",
        source="web",
        id=uuid4(),
    )
    setattr(row, column, Decimal(value) if column in {"amount", "fx_rate_to_base"} else value)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(row)
        db_session.flush()
